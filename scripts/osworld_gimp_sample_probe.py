"""Non-scoring official-VM probe for the GIMP Sample Colorize dialog."""
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

TARGET = 'IMG_7318_original.jpg'
SAMPLE = 'IMG_7328_edited.jpg'
OUTPUT = 'IMG_7318_edited.jpg'


def file_sha(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def controls(tree):
    text = str(tree or '')
    out = []
    if text.lstrip().startswith('<'):
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            root = None
        if root is not None:
            for node in root.iter():
                name = (node.attrib.get('name') or '').replace('\u200b', '').strip()
                coord = next((v for k, v in node.attrib.items() if k.endswith('}screencoord') or k == 'cp:screencoord'), '')
                size = next((v for k, v in node.attrib.items() if k.endswith('}size') or k == 'cp:size'), '')
                xy = re.findall(r'-?\d+', coord)
                wh = re.findall(r'\d+', size)
                if len(xy) == 2 and len(wh) == 2:
                    x, y = map(int, xy); w, h = map(int, wh)
                    out.append({'role': node.tag.rsplit('}', 1)[-1], 'name': name,
                                'x': x, 'y': y, 'w': w, 'h': h,
                                'cx': x + w // 2, 'cy': y + h // 2})
            return out


def matches(tree, label, role=None):
    return [
        c for c in controls(tree)
        if c['name'].casefold() == label.casefold()
        and (not role or c['role'].casefold() == role.casefold())
    ]


def unique(tree, label, role=None):
    hits = matches(tree, label, role)
    if len(hits) != 1:
        raise RuntimeError(f'CONTROL_NOT_UNIQUE:{label}:{len(hits)}')
    return hits[0]


def save_obs(root, name, obs):
    root.mkdir(parents=True, exist_ok=True)
    tree = str(obs.get('accessibility_tree') or '')
    (root / f'{name}.a11y.txt').write_text(tree, encoding='utf-8')
    shot = obs.get('screenshot')
    if isinstance(shot, (bytes, bytearray)):
        (root / f'{name}.png').write_bytes(shot)
    return tree


def step(env, command, pause=1):
    return env.step(command, pause=pause)[0]


def recover_control(env, obs, label, role=None, limit=12):
    """Re-observe until a control is freshly grounded; never reuse stale geometry."""
    for _ in range(limit):
        tree = (obs or {}).get('accessibility_tree')
        if tree and has(tree, label, role):
            return obs, unique(tree, label, role)
        obs = idle(env, 1)
    raise RuntimeError(f'CONTROL_REOBSERVE_TIMEOUT:{label}')


def click(env, obs, label, role=None, pause=1):
    obs, c = recover_control(env, obs, label, role)
    return step(env, f"pyautogui.click({c['cx']}, {c['cy']})", pause)


def has(tree, label, role=None):
    return len(matches(tree, label, role)) == 1


def idle(env, seconds=1):
    return step(env, f'pyautogui.sleep({int(seconds)})', seconds)


def profile_modal(tree):
    low = str(tree or '').casefold()
    return (
        ('convert to rgb working space?' in low or 'embedded color profile' in low)
        and has(tree, 'Keep', 'push-button')
    )


def _xml_root(tree):
    text = str(tree or '')
    if not text.lstrip().startswith('<'):
        return None
    try:
        return ET.fromstring(text)
    except ET.ParseError:
        return None


def _state(node, name):
    return next((v for k, v in node.attrib.items()
                 if k == name or k.endswith('}' + name)), '')


def gimp_visible(tree):
    """True only for a real GIMP process/window, never the GNOME dock launcher."""
    root = _xml_root(tree)
    if root is None:
        return False
    for node in root.iter():
        tag = node.tag.rsplit('}', 1)[-1]
        name = (node.attrib.get('name') or '').replace('\u200b', '').strip().casefold()
        if tag == 'application' and (name == 'gimp' or name.startswith('gimp-')):
            return True
        if tag == 'frame' and 'gimp' in name:
            if _state(node, 'visible') != 'false' and _state(node, 'showing') != 'false':
                return True
    return False


def active_gimp_document(tree, filename):
    root = _xml_root(tree)
    if root is None:
        return False
    stem = Path(str(filename)).stem.casefold()
    for node in root.iter():
        if node.tag.rsplit('}', 1)[-1] != 'frame':
            continue
        name = (node.attrib.get('name') or '').replace('\u200b', '').strip().casefold()
        if stem in name and 'gimp' in name and _state(node, 'active') == 'true':
            return True
    return False


def target_loaded(tree):
    return active_gimp_document(tree, TARGET) and not profile_modal(tree)


def chooser_ready(tree):
    return has(tree, SAMPLE, 'table-cell') and has(tree, 'Open', 'push-button')


def wait_for_target(env, obs, evidence, prefix, limit=45):
    launch_attempts = 0
    target_open_requested = False
    location_attempted = False
    for i in range(limit):
        tree = save_obs(evidence, f'{prefix}-{i:02d}', obs)
        if profile_modal(tree):
            obs = click(env, obs, 'Keep', 'push-button', 2)
            continue
        if target_loaded(tree):
            return obs
        if not gimp_visible(tree):
            if launch_attempts == 0 and has(tree, 'GNU Image Manipulation Program', 'push-button'):
                obs = click(env, obs, 'GNU Image Manipulation Program', 'push-button', 3)
                launch_attempts += 1
                continue
            if launch_attempts < 2:
                obs = step(env, "pyautogui.hotkey('ctrl', 'alt', 't'); pyautogui.sleep(0.8); pyautogui.write('gimp', interval=0.03); pyautogui.press('enter')", 3)
                launch_attempts += 1
                continue
            obs = idle(env, 1)
            continue
        if not target_open_requested and not has(tree, 'Open', 'push-button'):
            obs = step(env, "pyautogui.hotkey('ctrl', 'o')", 2)
            target_open_requested = True
            continue
        if has(tree, TARGET, 'table-cell') and has(tree, 'Open', 'push-button'):
            obs = click(env, obs, TARGET, 'table-cell')
            obs = click(env, obs, 'Open', 'push-button', 2)
            continue
        if has(tree, 'Open', 'push-button') and not location_attempted:
            obs = step(env, "pyautogui.hotkey('ctrl', 'l'); pyautogui.write('~/Pictures/' + TARGET, interval=0.03); pyautogui.press('enter')", 2)
            location_attempted = True
            continue
        obs = idle(env, 1)
    raise RuntimeError('TARGET_GIMP_STATE_NOT_READY')


def open_sample_reference(env, obs, evidence, limit=20):
    obs = step(env, "pyautogui.hotkey('ctrl', 'o')", 1)
    location_attempted = False
    for i in range(limit):
        tree = save_obs(evidence, f'20-open-stage-{i:02d}', obs)
        if profile_modal(tree):
            obs = click(env, obs, 'Keep', 'push-button', 2)
            continue
        if active_gimp_document(tree, SAMPLE) and not has(tree, 'Open', 'push-button'):
            return obs
        if has(tree, SAMPLE, 'table-cell') and has(tree, 'Open', 'push-button'):
            obs = click(env, obs, SAMPLE, 'table-cell')
            obs = click(env, obs, 'Open', 'push-button', 2)
            continue
        if has(tree, 'Open', 'push-button') and not location_attempted:
            obs = step(env, "pyautogui.hotkey('ctrl', 'l'); pyautogui.write('~/Pictures/' + SAMPLE, interval=0.03); pyautogui.press('enter')", 2)
            location_attempted = True
            continue
        obs = idle(env, 1)
    raise RuntimeError('SAMPLE_REFERENCE_NOT_READY')


def wait_for_control(env, obs, evidence, prefix, label, role=None, limit=20):
    for i in range(limit):
        tree=save_obs(evidence,f"{prefix}-{i:02d}",obs)
        if has(tree,label,role): return obs,tree
        obs=idle(env,1)
    raise RuntimeError(f"CONTROL_TIMEOUT:{label}")

def editable_text_values(tree):
    text = str(tree or '')
    if not text.lstrip().startswith('<'):
        return []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    values = []
    for node in root.iter():
        if node.tag.rsplit('}', 1)[-1] != 'text':
            continue
        editable = any(k.endswith('}editable') and v == 'true' for k, v in node.attrib.items())
        if editable:
            values.append((node.text or '').replace('\u200b', '').strip())
    return values


def export_alert_name(tree):
    low = str(tree or '')
    m = re.search(r'A file named &quot;([^&]+)&quot; already exists', low)
    return m.group(1) if m else ''


def prove_export_via_gui(env, obs, evidence):
    obs=click(env,obs,'Get Sample Colors','push-button',2); save_obs(evidence,'50-sample-colors-loaded',obs)
    obs=click(env,obs,'Apply','push-button',2); save_obs(evidence,'60-colorize-applied',obs)
    obs=click(env,obs,'Close','push-button',2); save_obs(evidence,'70-colorize-closed',obs)
    output_path='/home/user/Pictures/' + OUTPUT
    if env.controller.get_file(output_path) is not None:
        raise RuntimeError('OUTPUT_PREEXISTED_BEFORE_EXPORT')
    (evidence/'output-absent-before-export.txt').write_text(output_path+'\n',encoding='utf-8')
    obs=step(env,"pyautogui.hotkey('ctrl','shift','e')",2)
    obs,tree=wait_for_control(env,obs,evidence,'80-export-open','Export','push-button')

    # Export As is already rooted in the source image folder. Select Pictures explicitly,
    # then edit the dedicated Name field (Alt+N) instead of abusing Ctrl+L.
    if has(tree,'Pictures','table-cell'):
        obs=click(env,obs,'Pictures','table-cell',1)
    obs=step(env,"pyautogui.hotkey('alt','n'); pyautogui.hotkey('ctrl','a'); pyautogui.write('"+OUTPUT+"', interval=0.02)",1)
    tree=save_obs(evidence,'81-export-name',obs)
    values=editable_text_values(tree)
    if OUTPUT not in values:
        raise RuntimeError('EXPORT_NAME_NOT_SET')
    if TARGET in values:
        raise RuntimeError('EXPORT_NAME_STILL_ORIGINAL')

    obs=click(env,obs,'Export','push-button',2)
    for i in range(12):
        tree=save_obs(evidence,f'82-export-state-{i:02d}',obs)
        low=tree.casefold()
        alert=export_alert_name(tree)
        if alert:
            if alert.casefold()==TARGET.casefold():
                raise RuntimeError('ORIGINAL_OVERWRITE_ATTEMPT_BLOCKED')
            if alert.casefold()==OUTPUT.casefold():
                raise RuntimeError('OUTPUT_PREEXISTED_PROVENANCE_UNSAFE')
        if has(tree,'Export Image as JPEG','dialog'):
            # The JPEG modal overlays the parent Export dialog, so two buttons share
            # the label 'Export'. Use the active modal accelerator instead of a
            # globally ambiguous accessibility target.
            obs=step(env,"pyautogui.hotkey('alt','e')",2)
            continue
        export_dialog = has(tree,'Export Image','dialog') or has(tree,'Export Image as JPEG','dialog')
        if gimp_visible(tree) and not export_dialog:
            break
        obs=idle(env,1)
    else:
        raise RuntimeError('EXPORT_DIALOG_DID_NOT_SETTLE')

    # Prove bytes through the official controller before any chooser-based visual proof.
    data = env.controller.get_file(output_path)
    if not isinstance(data, (bytes, bytearray)) or len(data) < 1024:
        raise RuntimeError('EXPORTED_OUTPUT_BYTES_UNPROVEN')
    digest = hashlib.sha256(data).hexdigest()
    (evidence/'exported-output.sha256').write_text(digest+'  '+OUTPUT+'\n',encoding='utf-8')
    (evidence/'exported-output.bytes').write_text(str(len(data))+'\n',encoding='utf-8')
    (evidence/OUTPUT).write_bytes(data)

    obs=step(env,"pyautogui.hotkey('ctrl','o')",2)
    tree=save_obs(evidence,'90-output-chooser',obs)
    if has(tree,'Pictures','table-cell'):
        obs=click(env,obs,'Pictures','table-cell',1)
        tree=save_obs(evidence,'91-output-pictures',obs)
    if not has(tree,OUTPUT,'table-cell'):
        raise RuntimeError('EXPORTED_OUTPUT_NOT_VISIBLE_IN_CHOOSER')
    return obs,tree,{'bytes':len(data),'sha256':digest}

def main(image, evidence):
    if (
        os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted'
        or os.environ.get('ZERO_SPEND_MODE') != 'HARD'
    ):
        raise RuntimeError('CLOUD_ZERO_SPEND_PROBE_REQUIRED')

    from desktop_env.desktop_env import DesktopEnv
    from task_loader import load_task_from_file

    task = load_task_from_file('evaluation_examples/task_class/task_061.py')
    evidence = Path(evidence)
    evidence.mkdir(parents=True, exist_ok=True)
    base_before = file_sha(image)
    env = None
    proof = {
        'purpose': 'GIMP Sample Colorize UI probe only; no evaluator/score',
        'candidate_sha': os.environ.get('GITHUB_SHA'),
        'zero_spend_mode': 'HARD',
        'heavy_local': 0,
        'status': 'NOT_PROVEN',
    }

    try:
        env = DesktopEnv(
            provider_name='docker',
            path_to_vm=str(image),
            headless=True,
            action_space='pyautogui',
            require_a11y_tree=True,
            volume_size=50,
        )
        obs = env.reset(task_config=task)
        obs = wait_for_target(env, obs, evidence, '00-startup')
        obs = open_sample_reference(env, obs, evidence)
        tree = save_obs(evidence, '31-sample-opened', obs)
        if profile_modal(tree):
            obs = click(env, obs, 'Keep', 'push-button', 2)
            save_obs(evidence, '32-sample-profile-kept', obs)

        obs = step(env, "pyautogui.hotkey('ctrl', 'pageup')", 1)
        tree = save_obs(evidence, '40-target-active', obs)
        if TARGET.casefold() not in tree.casefold():
            raise RuntimeError('TARGET_NOT_ACTIVE_AFTER_SAMPLE')

        obs = step(env, "pyautogui.press('/'); pyautogui.sleep(0.6); pyautogui.write('Sample Colorize', interval=0.04); pyautogui.sleep(1); pyautogui.press('enter')", 2)
        tree = save_obs(evidence, '43-sample-colorize-dialog', obs)
        labels = [
            {'role': c['role'], 'name': c['name']}
            for c in controls(tree)
            if c['name']
        ]
        obs, output_tree, output_proof = prove_export_via_gui(env, obs, evidence)
        proof.update(status='EXPORT_PROVEN', dialog_controls=labels[-160:], output=OUTPUT,
                     output_visible_in_chooser=has(output_tree, OUTPUT, 'table-cell'),
                     output_bytes=output_proof['bytes'], output_sha256=output_proof['sha256'])
    finally:
        if env is not None:
            env.close()
        base_after = file_sha(image)
        proof.update(qcow_base_before=base_before, qcow_base_after=base_after)
        if base_before != base_after:
            proof['status'] = 'NOT_PROVEN'
            proof['failure'] = 'PINNED_QCOW_BASE_MODIFIED'
        (evidence / 'probe-result.json').write_text(
            json.dumps(proof, indent=2), encoding='utf-8'
        )
        if base_before != base_after:
            raise RuntimeError('PINNED_QCOW_BASE_MODIFIED')

    if proof['status'] != 'EXPORT_PROVEN':
        raise RuntimeError('GIMP_STYLE_EXPORT_UNPROVEN')
    print(json.dumps({
        'status': proof['status'],
        'output': proof.get('output'),
        'controls': len(proof.get('dialog_controls', [])),
    }))


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]))

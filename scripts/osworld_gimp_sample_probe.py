"""Non-scoring official-VM probe for the GIMP Sample Colorize dialog."""
import hashlib, json, os, re, sys
from pathlib import Path


def file_sha(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def controls(tree):
    out = []
    for line in str(tree or '').splitlines():
        cols = line.split('\t')
        if len(cols) < 7:
            continue
        xy = re.findall(r'-?\d+', cols[-2]); wh = re.findall(r'\d+', cols[-1])
        if len(xy) != 2 or len(wh) != 2:
            continue
        x, y = map(int, xy); w, h = map(int, wh)
        out.append(dict(role=cols[0], name=cols[1].replace('\u200b', '').strip(),
                        x=x, y=y, w=w, h=h, cx=x+w//2, cy=y+h//2))
    return out


def matches(tree, label, role=None):
    return [c for c in controls(tree) if c['name'].casefold() == label.casefold()
            and (not role or c['role'].casefold() == role.casefold())]


def unique(tree, label, role=None):
    hits = matches(tree, label, role)
    if len(hits) != 1:
        raise RuntimeError('CONTROL_NOT_UNIQUE:' + label + ':' + str(len(hits)))
    return hits[0]


def save_obs(root, name, obs):
    root.mkdir(parents=True, exist_ok=True)
    tree = str(obs.get('accessibility_tree') or '')
    (root / (name + '.a11y.txt')).write_text(tree, encoding='utf-8')
    shot = obs.get('screenshot')
    if isinstance(shot, (bytes, bytearray)):
        (root / (name + '.png')).write_bytes(shot)
    return tree


def click(env, obs, label, role=None, pause=1):
    c = unique(obs['accessibility_tree'], label, role)
    command = f"pyautogui.click({c['cx']}, {c['cy']})"
    return env.step(command, pause=pause)[0]


def click_if_unique(env, obs, label, role=None, pause=1):
    hits = matches(obs.get('accessibility_tree'), label, role)
    if len(hits) > 1:
        raise RuntimeError('CONTROL_NOT_UNIQUE:' + label + ':' + str(len(hits)))
    if not hits:
        return obs, False
    return click(env, obs, label, role, pause), True


def key(env, command, pause=1):
    return env.step(command, pause=pause)[0]


def main(image, evidence):
    if os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted' or os.environ.get('ZERO_SPEND_MODE') != 'HARD':
        raise RuntimeError('CLOUD_ZERO_SPEND_PROBE_REQUIRED')
    from desktop_env.desktop_env import DesktopEnv
    from task_loader import load_task_from_file
    task = load_task_from_file('evaluation_examples/task_class/task_061.py')
    evidence = Path(evidence); evidence.mkdir(parents=True, exist_ok=True)
    base_before = file_sha(image); env = None
    proof = {'purpose': 'GIMP Sample Colorize UI probe only; no evaluator/score',
             'candidate_sha': os.environ.get('GITHUB_SHA'), 'zero_spend_mode': 'HARD',
             'heavy_local': 0, 'status': 'NOT_PROVEN'}
    try:
        env = DesktopEnv(provider_name='docker', path_to_vm=str(image), headless=True,
                         action_space='pyautogui', require_a11y_tree=True, volume_size=50)
        obs = env.reset(task_config=task); save_obs(evidence, '00-reset', obs)

        # Reset can expose a staged file chooser over an already-open target image.
        # Dismiss only when Cancel is an exact, unique observed control.
        obs, dismissed = click_if_unique(env, obs, 'Cancel', 'push-button')
        if dismissed:
            save_obs(evidence, '01-initial-chooser-cancelled', obs)

        obs, kept = click_if_unique(env, obs, 'Keep', 'push-button')
        if kept:
            save_obs(evidence, '02-target-profile-kept', obs)

        obs = key(env, "pyautogui.hotkey('ctrl', 'o')")
        save_obs(evidence, '03-open-chooser', obs)
        obs = click(env, obs, 'IMG_7328_edited.jpg', 'table-cell')
        save_obs(evidence, '04-sample-selected', obs)
        obs = click(env, obs, 'Open', 'push-button', 2)
        save_obs(evidence, '05-sample-opened', obs)
        obs, kept = click_if_unique(env, obs, 'Keep', 'push-button')
        if kept:
            save_obs(evidence, '06-sample-profile-kept', obs)

        obs = key(env, "pyautogui.hotkey('ctrl', 'pageup')")
        save_obs(evidence, '07-target-active', obs)
        obs = click(env, obs, 'Colors', 'menu')
        save_obs(evidence, '08-colors-open', obs)
        obs = click(env, obs, 'Map', 'menu-item')
        save_obs(evidence, '09-map-open', obs)
        obs = click(env, obs, 'Sample Colorize', 'menu-item', 2)
        tree = save_obs(evidence, '10-sample-colorize-dialog', obs)
        labels = [{'role': c['role'], 'name': c['name']} for c in controls(tree) if c['name']]
        proof.update(status='DIALOG_PROVEN', dialog_controls=labels[-120:])
    finally:
        if env is not None:
            env.close()
        base_after = file_sha(image)
        proof.update(qcow_base_before=base_before, qcow_base_after=base_after)
        if base_before != base_after:
            proof['status'] = 'NOT_PROVEN'; proof['failure'] = 'PINNED_QCOW_BASE_MODIFIED'
        (evidence / 'probe-result.json').write_text(json.dumps(proof, indent=2), encoding='utf-8')
        if base_before != base_after:
            raise RuntimeError('PINNED_QCOW_BASE_MODIFIED')
    if proof['status'] != 'DIALOG_PROVEN':
        raise RuntimeError('SAMPLE_COLORIZE_DIALOG_UNPROVEN')
    print(json.dumps({'status': proof['status'], 'controls': len(proof.get('dialog_controls', []))}))


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]))

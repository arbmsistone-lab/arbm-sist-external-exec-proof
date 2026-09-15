"""Non-scoring official-VM probe for the GIMP Sample Colorize dialog."""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

TARGET = 'IMG_7318_original.jpg'
SAMPLE = 'IMG_7328_edited.jpg'


def file_sha(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def controls(tree):
    out = []
    for line in str(tree or '').splitlines():
        cols = line.split('\t')
        if len(cols) < 7:
            continue
        xy = re.findall(r'-?\d+', cols[-2])
        wh = re.findall(r'\d+', cols[-1])
        if len(xy) != 2 or len(wh) != 2:
            continue
        x, y = map(int, xy)
        w, h = map(int, wh)
        out.append({
            'role': cols[0],
            'name': cols[1].replace('\u200b', '').strip(),
            'x': x,
            'y': y,
            'w': w,
            'h': h,
            'cx': x + w // 2,
            'cy': y + h // 2,
        })
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


def click(env, obs, label, role=None, pause=1):
    c = unique(obs['accessibility_tree'], label, role)
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


def target_loaded(tree):
    low = str(tree or '').casefold()
    return (
        TARGET.casefold() in low
        and 'gnu image manipulation program' in low
        and not profile_modal(tree)
    )


def chooser_ready(tree):
    return has(tree, SAMPLE, 'table-cell') and has(tree, 'Open', 'push-button')


def wait_for_target(env, obs, evidence, prefix, limit=12):
    for i in range(limit):
        tree = save_obs(evidence, f'{prefix}-{i:02d}', obs)
        if profile_modal(tree):
            obs = click(env, obs, 'Keep', 'push-button', 2)
            continue
        if target_loaded(tree):
            return obs
        obs = idle(env, 1)
    raise RuntimeError('TARGET_GIMP_STATE_NOT_READY')


def open_sample_chooser(env, obs, evidence, limit=10):
    obs = step(env, "pyautogui.hotkey('ctrl', 'o')", 1)
    for i in range(limit):
        tree = save_obs(evidence, f'20-open-stage-{i:02d}', obs)
        if profile_modal(tree):
            obs = click(env, obs, 'Keep', 'push-button', 2)
            obs = wait_for_target(env, obs, evidence, '21-post-profile', 6)
            obs = step(env, "pyautogui.hotkey('ctrl', 'o')", 1)
            continue
        if chooser_ready(tree):
            return obs
        obs = idle(env, 1)
    raise RuntimeError('SAMPLE_CHOOSER_NOT_READY')


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
        obs = open_sample_chooser(env, obs, evidence)

        obs = click(env, obs, SAMPLE, 'table-cell')
        save_obs(evidence, '30-sample-selected', obs)
        obs = click(env, obs, 'Open', 'push-button', 2)
        tree = save_obs(evidence, '31-sample-opened', obs)
        if profile_modal(tree):
            obs = click(env, obs, 'Keep', 'push-button', 2)
            save_obs(evidence, '32-sample-profile-kept', obs)

        obs = step(env, "pyautogui.hotkey('ctrl', 'pageup')", 1)
        tree = save_obs(evidence, '40-target-active', obs)
        if TARGET.casefold() not in tree.casefold():
            raise RuntimeError('TARGET_NOT_ACTIVE_AFTER_SAMPLE')

        obs = click(env, obs, 'Colors', 'menu')
        save_obs(evidence, '41-colors-open', obs)
        obs = click(env, obs, 'Map', 'menu-item')
        save_obs(evidence, '42-map-open', obs)
        obs = click(env, obs, 'Sample Colorize', 'menu-item', 2)
        tree = save_obs(evidence, '43-sample-colorize-dialog', obs)
        labels = [
            {'role': c['role'], 'name': c['name']}
            for c in controls(tree)
            if c['name']
        ]
        proof.update(status='DIALOG_PROVEN', dialog_controls=labels[-160:])
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

    if proof['status'] != 'DIALOG_PROVEN':
        raise RuntimeError('SAMPLE_COLORIZE_DIALOG_UNPROVEN')
    print(json.dumps({
        'status': proof['status'],
        'controls': len(proof.get('dialog_controls', [])),
    }))


if __name__ == '__main__':
    main(Path(sys.argv[1]), Path(sys.argv[2]))

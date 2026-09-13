"""Pure recovery policy for OSWorld v32; no network or guest access."""
import re

VISUAL_MARKERS = (
    '.jpg', '.jpeg', '.png', '.webp', '.gif', 'image', 'photo', 'picture',
    'color grading', 'gimp', 'darktable', 'libreoffice impress', 'geogebra',
)


def is_visual_task(instruction, active_application=''):
    text = (str(instruction or '') + ' ' + str(active_application or '')).casefold()
    return any(marker in text for marker in VISUAL_MARKERS)


def semantic_terminal(stalled, verifier_no_progress):
    """Semantic predicates cannot terminate while independent GUI progress continues."""
    return int(stalled) >= 24 and int(verifier_no_progress) >= 6


def rejects_visual_navigation_loop(action, instruction, active_application, stalled):
    """Reject a repeated file-open shortcut after visual progress has stalled.

    It intentionally recognizes only the unambiguous Ctrl+O loop captured in
    the 061 artifact. Other file-dialog actions remain available, because an
    agent may still need to deliberately open a visible target or reference.
    """
    if not is_visual_task(instruction, active_application) or int(stalled) < 4:
        return False
    command = str((action or {}).get('command') or '')
    return bool(re.search(r"pyautogui\.hotkey\(\s*['\"]ctrl['\"]\s*,\s*['\"]o['\"]\s*\)", command, re.I))


def recovery_policy(instruction, active_application, stalled, verifier_no_progress,
                    recovery_level, current_provider='', visual_capacity_exhausted=False):
    visual = is_visual_task(instruction, active_application)
    result = {'visual_task': visual, 'provider_hint': None, 'strategy': None}
    if int(stalled) >= 6:
        if visual:
            result['strategy'] = (
                'Visual task has no verified semantic milestone. Keep screenshot reasoning. '
                'Re-observe the foreground, use only task-visible paths (never /home/oai/share unless the task says so), use Ctrl+L in a GTK file chooser before typing a path, and verify the exact reference/target image or visible '
                'control before acting, and do not claim a tab/file switch unless the next '
                'foreground observation proves it. Advance toward the requested edit and export.'
            )
        else:
            result['strategy'] = (
                'No verified subtask milestone. Replan from last verified fact; read required '
                'source before switching to output app. Specify a testable checkpoint.'
            )
    if visual and visual_capacity_exhausted:
        result['provider_hint'] = 'text'
        result['strategy'] = (
            'VISUAL CAPACITY FALLBACK: the free screenshot-capable routes were unavailable repeatedly. '
            'Continue from the exact accessibility tree and verified milestones instead of waiting. '
            'Use only a visible, reversible control; re-request screenshot reasoning when it becomes available.'
        )
    elif int(stalled) >= 8:
        # Keep visual recovery provider-neutral so every healthy FREE multimodal route stays eligible.
        result['provider_hint'] = None if visual else 'text'
    elif int(recovery_level) >= 4:
        result['provider_hint'] = None if visual else ('groq' if current_provider == 'mistral-free' else 'mistral')
    return result

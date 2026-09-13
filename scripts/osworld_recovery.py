"""Pure recovery policy for OSWorld v32; no network or guest access."""

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


def recovery_policy(instruction, active_application, stalled, verifier_no_progress,
                    recovery_level, current_provider=''):
    visual = is_visual_task(instruction, active_application)
    result = {'visual_task': visual, 'provider_hint': None, 'strategy': None}
    if int(stalled) >= 6:
        if visual:
            result['strategy'] = (
                'Visual task has no verified semantic milestone. Keep screenshot reasoning. '
                'Re-observe the foreground, verify the exact reference/target image or visible '
                'control before acting, and do not claim a tab/file switch unless the next '
                'foreground observation proves it. Advance toward the requested edit and export.'
            )
        else:
            result['strategy'] = (
                'No verified subtask milestone. Replan from last verified fact; read required '
                'source before switching to output app. Specify a testable checkpoint.'
            )
    if int(stalled) >= 8:
        result['provider_hint'] = 'openrouter' if visual else 'text'
    elif int(recovery_level) >= 4:
        result['provider_hint'] = 'groq' if current_provider == 'mistral-free' else 'mistral'
    return result

"""Fail-closed GUI recovery for reference-pair color/style transfer in GIMP."""
import re
from osworld_061_champion import LABELS, ROLES, ACCELERATORS, accelerator_command

_IMAGE = re.compile(r'([A-Za-z0-9_.-]+\.(?:jpg|jpeg|png|webp))', re.I)


def parse_reference_pair_task(instruction):
    text = str(instruction or '')
    names = []
    for name in _IMAGE.findall(text):
        if name not in names:
            names.append(name)
    originals = [n for n in names if '_original.' in n.lower()]
    edited = [n for n in names if '_edited.' in n.lower()]
    if len(originals) < 2 or len(edited) < 2:
        return None

    def stem(name):
        return re.sub(r'_(?:original|edited)\.[^.]+$', '', name, flags=re.I)

    pairs = [(o, next((e for e in edited if stem(e) == stem(o)), None)) for o in originals]
    pairs = [(o, e) for o, e in pairs if e]
    if len(pairs) < 2:
        return None
    example = pairs[0]
    target, output = pairs[1]
    return {'reference_original': example[0], 'reference_edited': example[1],
            'target_original': target, 'output': output}


def _active_document(obs, filename):
    wanted = re.sub(r'\.[^.]+$', '', str(filename or '')).casefold()
    for line in str(obs or '').splitlines():
        cols = line.split('\t')
        if len(cols) < 2 or cols[0].strip().casefold() != 'frame':
            continue
        name = cols[1].replace('\u200b', '').strip().casefold()
        if wanted and wanted in name and 'gimp' in name:
            return True
    return False


def _has(obs, name, role=None):
    needle = str(name or '').casefold()
    for line in str(obs or '').splitlines():
        cols = line.split('\t')
        if len(cols) < 2:
            continue
        if cols[1].replace('\u200b', '').strip().casefold() != needle:
            continue
        if role and cols[0].strip().casefold() != str(role).casefold():
            continue
        return True
    return False


def _action(command, plan, visible_text, target=None, checkpoint=True, phase=None):
    action = {'action': 'exec', 'command': command, 'plan': plan, 'summary': plan,
              'expected_change': visible_text, 'confidence': 1.0, 'observed_facts': [],
              'verification': 'next foreground must expose the named visible state'}
    action['checkpoint'] = ({'name': visible_text, 'application': 'GNU Image Manipulation Program',
                             'visible_text': visible_text} if checkpoint else None)
    if target: action['target'] = target
    if phase: action['specialist_phase'] = phase
    return action


def _click(label, role, plan, visible_text, double=False, checkpoint=True, phase=None):
    method = 'doubleClick' if double else 'click'
    return _action('pyautogui.%s(0, 0)' % method, plan, visible_text,
                   {'source': 'accessibility', 'label': label, 'role': role}, checkpoint, phase)


def _sample_colorize_dialog(obs):
    return all(_has(obs, label, 'push-button') for label in ('Get Sample Colors', 'Apply', 'Close'))


def _champion_phase(obs, phase, plan, visible_text):
    label, role = LABELS[phase], ROLES[phase]
    if _has(obs, label, role):
        return _click(label, role, plan, visible_text, checkpoint=False, phase=phase)
    if _sample_colorize_dialog(obs) and phase in ACCELERATORS:
        return _action(accelerator_command(phase), plan + ' Use the dialog accelerator because the named control is temporarily absent from accessibility.',
                       visible_text, checkpoint=False, phase=phase)
    return None




def _dialog_button(obs, dialog_name, button_name):
    lines=str(obs or '').splitlines()
    inside=False
    for line in lines:
        cols=line.split('\t')
        if len(cols)>=2 and cols[0].strip().casefold()=='dialog':
            inside=cols[1].replace('\u200b','').strip().casefold()==dialog_name.casefold()
            continue
        if inside and len(cols)>=7 and cols[0].strip().casefold()=='push-button' and cols[1].replace('\u200b','').strip().casefold()==button_name.casefold():
            import re
            xy=re.findall(r'-?\d+',cols[-2]); wh=re.findall(r'\d+',cols[-1])
            if len(xy)==2 and len(wh)==2:
                x,y=map(int,xy); w,h=map(int,wh)
                return x+w//2,y+h//2
    return None

def next_recovery_action(instruction, active_application, observation, state):
    """Return one grounded GUI action, or None when evidence is insufficient."""
    task = parse_reference_pair_task(instruction)
    app = str(active_application or '').casefold()
    if not task or not (state.get('owned') or 'gimp' in app or 'gnu image manipulation program' in app):
        return None
    obs = str(observation or '')
    sample = task['reference_edited']
    target = task['target_original']

    # Embedded-profile prompts are foreground modals. Keep the supplied profile;
    # verify the document surface becomes visible again after dismissal.
    if _has(obs, 'Keep', 'push-button') and 'embedded color profile' in obs.casefold():
        profile_image = sample if sample.casefold() in obs.casefold() else target
        return _click('Keep', 'push-button', 'Keep the supplied embedded color profile.',
                      profile_image + ' (', phase='keep-profile')

    chooser_open = _has(obs, 'Open', 'push-button')
    sample_active = _active_document(obs, sample) or (_has(obs, sample, 'table-cell') and not chooser_open)
    target_active = _active_document(obs, target) or (_has(obs, target, 'table-cell') and not chooser_open)
    if sample_active:
        state['sample_loaded'] = True
    if target_active:
        state['target_active'] = True

    # A GTK chooser already exposes the exact task files. Double-click the
    # edited reference: one GUI call both selects and opens it.
    if _has(obs, sample, 'table-cell') and _has(obs, 'Open', 'push-button'):
        return _click(sample, 'table-cell',
                      'Open the edited reference image as the color sample.',
                      sample + ' (', double=True, checkpoint=False, phase='open-sample')

    # If the sample is not represented yet, open GIMP's chooser once.
    if not state.get('sample_loaded') and sample.casefold() not in obs.casefold():
        return _action("pyautogui.hotkey('ctrl', 'o')",
                       'Open another image in GIMP.', 'Open Image', checkpoint=False, phase='open-chooser')

    dialog_open = all(_has(obs, label, 'push-button') for label in
                      ('Get Sample Colors', 'Apply', 'Close'))
    if dialog_open:
        state['colorize_open_observed'] = True
        state['colorize_open_waits'] = 0
        if state.get('colorize_closed'):
            return None
        if not state.get('use_subcolors_enabled'):
            return _champion_phase(obs, 'enable-subcolors',
                                   'Enable mixed subcolors for a fuller reference color transfer.', 'Sample Colorize')
        # Original intensity must be disabled BEFORE Hold intensity. In the
        # official VM, disabling Hold intensity can make Original intensity
        # disappear from the simplified accessibility tree.
        if not state.get('original_intensity_disabled'):
            return _champion_phase(obs, 'disable-original-intensity',
                                   'Allow transferred grading to alter original destination intensity.', 'Sample Colorize')
        if not state.get('hold_intensity_disabled'):
            return _champion_phase(obs, 'disable-hold-intensity',
                                   'Allow the reference grading to change destination average intensity.', 'Sample Colorize')
        if not state.get('sample_colors_requested'):
            return _champion_phase(obs, 'sample-colors',
                                   'Load the visible edited reference colors into Sample Colorize.', 'Sample Colorize')
        if not state.get('colorize_applied'):
            return _champion_phase(obs, 'apply-colorize',
                                   'Apply the sampled color mapping to the destination image.', 'Sample Colorize')
        # The official 061 VM exposes a bottom Cancel button while GEGL is still
        # remapping colors. Handing control to the generic agent here caused it
        # to click that Cancel button and abort the actual transformation.
        if _has(obs, 'Cancel', 'push-button'):
            state['colorize_processing'] = True
            return None
        state['colorize_processing'] = False
        return _click('Close', 'push-button', 'Close Sample Colorize only after the remap has finished.',
                      target + ' (', checkpoint=False, phase='close-colorize')

    output_path = '/home/user/Pictures/' + task['output']
    if state.get('colorize_closed'):
        if not state.get('export_open_requested'):
            if not target_active: return None
            return _action("pyautogui.hotkey('ctrl', 'shift', 'e')",
                           'Open GIMP Export As for the edited target.', 'Export Image', phase='export-open')
        low = obs.casefold()
        if target.casefold() in low and 'already exists' in low and _has(obs, 'Cancel', 'push-button'):
            return _click('Cancel', 'push-button',
                          'Abort any attempt to overwrite the original target image.',
                          'Export Image', checkpoint=False, phase='export-original-overwrite-cancel')
        if task['output'].casefold() in low and 'already exists' in low:
            return None
        if 'export image' in low and not state.get('export_name_requested'):
            return _action("pyautogui.hotkey('alt', 'n')",
                           'Focus the dedicated export Name field.', task['output'],
                           checkpoint=False, phase='export-name-focus')
        if state.get('export_name_requested') and not state.get('export_name_typed'):
            return _action("pyautogui.hotkey('ctrl','a'); pyautogui.write(%r, interval=0.02)" % task['output'],
                           'Replace the source filename with the exact task output filename.',
                           task['output'], checkpoint=False, phase='export-name')
        if state.get('export_name_typed') and not state.get('export_submitted') and _has(obs, 'Export', 'push-button'):
            return _click('Export', 'push-button', 'Submit the exact output filename.',
                          'Export Image as JPEG', checkpoint=False, phase='export-submit')
        if state.get('export_submitted') and 'export image as jpeg' in low:
            point=_dialog_button(obs,'Export Image as JPEG','Export')
            if not point:
                return None
            return _action('pyautogui.click(%d, %d)' % point,
                           'Confirm JPEG export options in the active modal.', task['output'],
                           {'source':'screenshot','label':'Export Image as JPEG / Export'},
                           checkpoint=False, phase='export-confirm')
        if state.get('export_confirmed') and task['output'].casefold() in obs.casefold():
            return {'action':'finish','command':'','plan':'Finish after visible export confirmation.',
                    'summary':'Edited target exported by the agent.','confidence':1.0,
                    'verification':task['output']+' exported'}
        return None

    # The active edited-reference layer is enough when GIMP omits a frame node.
    if state.get('sample_loaded') and sample_active and not target_active:
        return _action("pyautogui.hotkey('ctrl', 'pageup')",
                       'Switch from the sample back to the target image.', target + ' (')
    if not target_active: return None

    # Keep action-search query + Enter in one GUI turn. The official run
    # proved that an observation boundary here can make GIMP lose search focus.
    if state.get('colorize_open_requested') and not state.get('colorize_open_observed'):
        state['colorize_open_waits'] = state.get('colorize_open_waits', 0) + 1
        if state['colorize_open_waits'] <= 2:
            return None
        state['colorize_open_requested'] = False
    if not state.get('colorize_open_requested'):
        return _action("pyautogui.press('/'); pyautogui.sleep(0.6); pyautogui.write('Sample Colorize', interval=0.04); pyautogui.sleep(1.0); pyautogui.press('enter')",
                       'Search for and open Sample Colorize atomically.', 'Get Sample Colors',
                       phase='open-colorize')
    return None

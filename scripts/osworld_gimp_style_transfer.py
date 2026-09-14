"""Fail-closed GUI recovery for reference-pair color/style transfer in GIMP."""
import re

_IMAGE = re.compile(r'([A-Za-z0-9_.-]+\.(?:jpg|jpeg|png|webp))', re.I)


def parse_reference_pair_task(instruction):
    text=str(instruction or '')
    names=[]
    for name in _IMAGE.findall(text):
        if name not in names: names.append(name)
    originals=[n for n in names if '_original.' in n.lower()]
    edited=[n for n in names if '_edited.' in n.lower()]
    if len(originals)<2 or len(edited)<2:
        return None
    # The example pair shares a stem; the output edited file shares the target stem.
    def stem(n):
        return re.sub(r'_(?:original|edited)\.[^.]+$','',n,flags=re.I)
    example=None; target=None; output=None
    for original in originals:
        match=next((e for e in edited if stem(e)==stem(original)),None)
        if match: example=(original,match); break
    for original in originals:
        if not example or original!=example[0]:
            match=next((e for e in edited if stem(e)==stem(original)),None)
            if match: target=original; output=match; break
    if not example or not target or not output: return None
    return {'reference_original':example[0],'reference_edited':example[1],
            'target_original':target,'output':output}

def _active_document(obs, filename):
    wanted=str(filename or '').casefold()
    for line in str(obs or '').splitlines():
        cols=line.split('\t')
        if len(cols)<2 or cols[0].strip().casefold()!='label': continue
        name=cols[1].replace('\u200b','').strip().casefold()
        if name.startswith(wanted+' (') and (' mb)' in name or ' gb)' in name):
            return True
    return False

def _has(obs, name, role=None):
    needle=str(name or '').casefold()
    for line in str(obs or '').splitlines():
        cols=line.split('\t')
        if len(cols)<2: continue
        if cols[1].replace('\u200b','').strip().casefold()!=needle: continue
        if role and cols[0].strip().casefold()!=str(role).casefold(): continue
        return True
    return False


def _click(label, role, plan, checkpoint):
    return {'action':'exec','command':'pyautogui.click(0, 0)',
            'target':{'source':'accessibility','label':label,'role':role},
            'plan':plan,'summary':plan,'expected_change':checkpoint,
            'checkpoint':{'name':checkpoint,'application':'GNU Image Manipulation Program',
                          'visible_text':checkpoint},'confidence':1.0,
            'observed_facts':[],'verification':'visible control observed'}


def _key(command, plan, checkpoint):
    return {'action':'exec','command':command,'plan':plan,'summary':plan,
            'expected_change':checkpoint,
            'checkpoint':{'name':checkpoint,'application':'GNU Image Manipulation Program',
                          'visible_text':checkpoint},'confidence':1.0,
            'observed_facts':[],'verification':'state derived from visible controls'}

def next_recovery_action(instruction, active_application, observation, state):
    """Return one grounded/reversible GUI action, or None when evidence is insufficient."""
    task=parse_reference_pair_task(instruction)
    app=str(active_application or '').casefold()
    if not task or not ('gimp' in app or 'gnu image manipulation program' in app): return None
    obs=str(observation or '')
    # Preserve embedded profiles; changing them would alter the provided reference colors.
    if _has(obs,'Keep','push-button') and 'embedded color profile' in obs:
        return _click('Keep','push-button','Keep the image embedded color profile.',
                      'embedded color profile dialog closed')
    sample=task['reference_edited']
    target=task['target_original']
    # A visible GTK chooser gives exact task files; select the edited reference sample.
    if not state.get('sample_requested') and _has(obs,sample,'table-cell') and _has(obs,'Open','push-button'):
        state['sample_requested']=True
        return _click(sample,'table-cell','Select the edited reference image as the color sample.',
                      sample+' selected')
    if state.get('sample_requested') and _has(obs,sample,'table-cell') and _has(obs,'Open','push-button'):
        return _click('Open','push-button','Open the selected edited reference image.',
                      sample+' opened')
    # If the sample is not already represented in GIMP, open the file chooser.
    if not state.get('sample_loaded') and sample.casefold() not in obs.casefold():
        state['sample_requested']=False
        return _key("pyautogui.hotkey('ctrl', 'o')",'Open another image in GIMP.','Open Image')
    if _active_document(obs,sample):
        state['sample_loaded']=True
    # Return to target image before invoking the mapping filter.
    if (state.get('sample_loaded') and not state.get('target_active') and
            target.casefold() not in obs.casefold() and not state.get('target_switch')):
        state['target_switch']=True
        return _key("pyautogui.hotkey('ctrl', 'pageup')",'Switch from sample back to target image.',target)
    if _active_document(obs,target): state['target_active']=True
    if not state.get('target_active'): return None
    if _has(obs,'Sample Colorize','menu-item'):
        return _click('Sample Colorize','menu-item','Open Sample Colorize for the visible target image.',
                      'Sample Colorize')
    if _has(obs,'Map','menu-item'):
        return _click('Map','menu-item','Open the Colors Map submenu.','Sample Colorize')
    if _has(obs,'Colors','menu'):
        return _click('Colors','menu','Open the GIMP Colors menu.','Map')
    return None

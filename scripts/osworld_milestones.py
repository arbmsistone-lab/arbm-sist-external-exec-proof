"""Independent semantic predicates over foreground observations, never guest state."""
import re
from osworld_control import foreground_context,tree_signature

def normalized(value):return re.sub(r'\s+',' ',str(value).replace('\u200b','')).strip().casefold()

_CONTENT_ROLES={'heading','paragraph','list-item','static','text','section'}

def meaningful_content_lines(value):
    """Return substantial foreground content, excluding UI chrome and metadata."""
    out=set()
    for raw in str(value or '').splitlines():
        if raw.startswith(('ACTIVE APPLICATION','BACKGROUND DESKTOP','[Compacted')):
            continue
        parts=raw.split('\t')
        if not parts or normalized(parts[0]) not in _CONTENT_ROLES:
            continue
        fields=[normalized(x) for x in parts[1:3] if normalized(x)]
        if not fields:
            continue
        text=max(fields,key=len)
        if len(text)<24 or set(text)<=set('•-–— .'):
            continue
        out.add(text[:700])
    return out

class Milestones:
    def __init__(self):
        self.pending=None;self.verified=[];self.stalled=0;self.last={'status':'initial'}
    def expect(self,action,observation):
        candidate=action.get('checkpoint')
        focused,app=foreground_context(observation)
        self.pending={
            'predicate':candidate,
            'before':tree_signature(focused),
            'before_text':normalized(focused),
            'before_app':app,
            'before_content':sorted(meaningful_content_lines(focused)),
        }
    def observe(self,observation):
        if self.pending is None:return {'status':'IDLE','stalled_actions':self.stalled}
        pending=self.pending;self.pending=None;self.stalled+=1
        focused,app=foreground_context(observation);candidate=pending['predicate']
        self.last={'status':'UNVERIFIED','reason':'missing_or_unmatched_predicate','stalled_actions':self.stalled}
        if not isinstance(candidate,dict):return self.last
        name,expected,text=(str(candidate.get(k) or '').strip() for k in ('name','application','visible_text'))
        visible=normalized(text)
        after_text=normalized(focused)
        after_sig=tree_signature(focused)
        app_changed=normalized(app)!=normalized(pending['before_app'])
        anchor_new=visible not in pending['before_text'] or app_changed
        before_content=set(pending.get('before_content') or [])
        after_content=meaningful_content_lines(focused)
        new_content=sorted(after_content-before_content)
        # A pre-existing anchor (for example an inbox subject) is not sufficient by
        # itself. It may prove navigation only when the same foreground undergoes a
        # structural change and at least two substantial new content lines appear.
        semantic_transition=(
            not anchor_new
            and normalized(expected)==normalized(app)
            and visible in after_text
            and pending['before']!=after_sig
            and len(new_content)>=2
        )
        matched=(4<=len(name)<=200 and 4<=len(visible)<=300 and normalized(expected)==normalized(app)
                 and app not in ('unknown','Desktop') and visible in after_text
                 and pending['before']!=after_sig and (anchor_new or semantic_transition))
        key=(normalized(expected),visible)
        if matched and not any((normalized(m['application']),normalized(m['visible_text']))==key for m in self.verified):
            proof={'name':name,'application':app,'visible_text':text,'observation_sha256':after_sig,
                   'verification_basis':'anchor_new' if anchor_new else 'foreground_content_transition',
                   'new_content_count':len(new_content)}
            self.verified.append(proof);self.verified=self.verified[-40:];self.stalled=0
            self.last={'status':'VERIFIED','milestone':proof,'stalled_actions':0}
        return self.last
    def context(self):return {'last_check':self.last,'verified':self.verified[-10:],'stalled_actions':self.stalled}

def verified_facts(action,observation):
    focused,app=foreground_context(observation)
    if app=='unknown':return []
    # Never use our metadata prefix (which names hidden files) as source evidence.
    actual='\n'.join(x for x in focused.splitlines() if not x.startswith(('ACTIVE APPLICATION','BACKGROUND DESKTOP','[Compacted')))
    facts=action.get('observed_facts');out=[]
    if not isinstance(facts,list):return out
    for item in facts[:8]:
        if not isinstance(item,dict):continue
        quote=str(item.get('quote') or '').strip()
        if 8<=len(quote)<=600 and normalized(quote) in normalized(actual):
            out.append({'application':app,'quote':quote,'observation_sha256':tree_signature(focused)})
    return out

"""Independent semantic predicates over foreground observations, never guest state."""
import re
from osworld_control import foreground_context,tree_signature

def normalized(value):return re.sub(r'\s+',' ',str(value).replace('\u200b','')).strip().casefold()

class Milestones:
    def __init__(self):
        self.pending=None;self.verified=[];self.stalled=0;self.last={'status':'initial'}
    def expect(self,action,observation):
        candidate=action.get('checkpoint')
        focused,app=foreground_context(observation)
        self.pending={'predicate':candidate,'before':tree_signature(focused),'before_text':normalized(focused),'before_app':app}
    def observe(self,observation):
        if self.pending is None:return self.last
        pending=self.pending;self.pending=None;self.stalled+=1
        focused,app=foreground_context(observation);candidate=pending['predicate']
        self.last={'status':'UNVERIFIED','reason':'missing_or_unmatched_predicate','stalled_actions':self.stalled}
        if not isinstance(candidate,dict):return self.last
        name,expected,text=(str(candidate.get(k) or '').strip() for k in ('name','application','visible_text'))
        visible=normalized(text)
        # A label already present in the same foreground is not a new milestone.
        newly_visible=visible not in pending['before_text'] or normalized(app)!=normalized(pending['before_app'])
        matched=(4<=len(name)<=200 and 4<=len(visible)<=300 and normalized(expected)==normalized(app)
                 and app not in ('unknown','Desktop') and visible in normalized(focused)
                 and newly_visible and pending['before']!=tree_signature(focused))
        key=(normalized(expected),visible)
        if matched and not any((normalized(m['application']),normalized(m['visible_text']))==key for m in self.verified):
            proof={'name':name,'application':app,'visible_text':text,'observation_sha256':tree_signature(focused)}
            self.verified.append(proof);self.verified=self.verified[-40:];self.stalled=0
            self.last={'status':'VERIFIED','milestone':proof,'stalled_actions':0}
        return self.last
    def context(self):return {'last_check':self.last,'verified':self.verified[-10:],'stalled_actions':self.stalled}

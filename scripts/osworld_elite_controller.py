"""Elite control plane: progress-ledger, tabu backtracking, and latency gates.

Pure logic only: no network, no guest access, no benchmark-specific shortcuts.
"""
from collections import Counter, deque
import hashlib
import math
import statistics


def action_fingerprint(command, target=None):
    clean = ' '.join(str(command or '').split())
    if isinstance(target,dict) and str(target.get('label') or '').strip():
        import re
        method=(re.search(r'pyautogui\.(\w+)',clean) or [None,'exec'])[1]
        clean='|'.join((method,str(target.get('source') or '').casefold(),str(target.get('role') or '').casefold(),str(target.get('label') or '').strip().casefold()))
    return hashlib.sha256(clean.encode()).hexdigest()[:16]


class EliteController:
    """Fast/slow/replan controller driven only by observed execution evidence."""
    def __init__(self, fast_latency_s=8.0, hard_latency_s=20.0,
                 max_waits=2, max_stall=3, tabu_size=24):
        self.fast_latency_s = float(fast_latency_s)
        self.hard_latency_s = float(hard_latency_s)
        self.max_waits = int(max_waits)
        self.max_stall = int(max_stall)
        self.failed_actions = deque(maxlen=int(tabu_size))
        self.evidence_retry_fingerprints = set()
        self.pending_action = None
        self.latencies = deque(maxlen=32)
        self.checkpoints = deque(maxlen=16)
        self.backtrack_events = 0
        self.stall = 0
        self.waits = 0
        self.issued = 0
        self.progress_events = 0
        self.no_progress_events = 0
        self.wait_events = 0

    def before_action(self, command, target=None, retry_proof=None):
        fp = action_fingerprint(command,target)
        if fp in self.failed_actions:
            proof = retry_proof if isinstance(retry_proof,dict) else {}
            bounded = (
                proof.get('fresh_observation') is True
                and proof.get('state_changed') is True
                and proof.get('bounded_retry') is True
                and bool(str(proof.get('reason') or '').strip())
                and fp not in self.evidence_retry_fingerprints
            )
            if not bounded:
                return {'allow': False, 'mode': 'replan', 'reason': 'tabu_failed_action',
                        'fingerprint': fp}
            self.evidence_retry_fingerprints.add(fp)
            self.pending_action = fp
            self.issued += 1
            return {'allow': True, 'mode': self.decision()['mode'],
                    'reason': 'evidence_bounded_retry', 'fingerprint': fp}
        self.pending_action = fp
        self.issued += 1
        return {'allow': True, 'mode': self.decision()['mode'],
                'reason': 'action_admitted', 'fingerprint': fp}

    def observe(self, progress):
        """Close the pending action using the next independent observation."""
        progress = bool(progress)
        if self.pending_action is not None:
            if progress:
                self.progress_events += 1
                self.stall = 0
                self.waits = 0
            else:
                self.no_progress_events += 1
                self.stall += 1
                self.failed_actions.append(self.pending_action)
                if self.stall == self.max_stall and self.checkpoints:
                    self.backtrack_events += 1
            self.pending_action = None
        elif progress:
            self.progress_events += 1
            self.stall = 0
            self.waits = 0
        return self.decision()

    def note_wait(self):
        self.waits += 1
        self.wait_events += 1
        return self.decision()

    def checkpoint(self, proof):
        if not isinstance(proof,dict):
            return self.recovery_anchor()
        item={k:str(proof.get(k) or '')[:300] for k in ('name','application','visible_text','observation_sha256')}
        key=(item['application'].casefold(),item['visible_text'].casefold(),item['observation_sha256'])
        if item['application'] and item['visible_text'] and not any(
                (x['application'].casefold(),x['visible_text'].casefold(),x['observation_sha256'])==key
                for x in self.checkpoints):
            self.checkpoints.append(item)
        return self.recovery_anchor()

    def recovery_anchor(self):
        return {
            'last_verified_checkpoint': dict(self.checkpoints[-1]) if self.checkpoints else None,
            'checkpoint_count': len(self.checkpoints),
            'tabu_action_count': len(self.failed_actions),
            'backtrack_events': self.backtrack_events,
        }

    def reset(self):
        self.waits = 0
        self.stall = 0
        self.latencies.clear()
        self.pending_action = None
        self.failed_actions.clear()
        self.evidence_retry_fingerprints.clear()
        self.checkpoints.clear()
        self.backtrack_events = 0
        self.issued = 0
        self.progress_events = 0
        self.no_progress_events = 0
        self.wait_events = 0
        return self.metrics()

    def record_latency(self, latency_s):
        try:
            value = float(latency_s)
        except (TypeError, ValueError):
            return self.decision()
        if math.isfinite(value):
            self.latencies.append(max(0.0, value))
        return self.decision()

    def decision(self):
        recent = list(self.latencies)[-8:]
        p95 = max(recent) if recent else 0.0
        if self.waits >= self.max_waits:
            return self._state('replan', 'wait_budget', p95)
        if self.stall >= self.max_stall:
            if self.checkpoints:
                return self._state('replan', 'checkpoint_backtrack', p95)
            return self._state('replan', 'progress_budget', p95)
        if p95 > self.hard_latency_s:
            return self._state('replan', 'latency_hard', p95)
        if p95 > self.fast_latency_s or self.stall >= 2:
            return self._state('slow', 'latency_or_uncertainty', p95)
        return self._state('fast', 'healthy', p95)

    def _state(self, mode, reason, latency):
        return {'mode': mode, 'reason': reason, 'stall': self.stall,
                'waits': self.waits, 'latency_s': round(latency, 3),
                'tabu_actions': len(self.failed_actions)}

    def metrics(self):
        xs = list(self.latencies)
        completed = self.progress_events + self.no_progress_events
        progress_ratio = self.progress_events / completed if completed else 0.0
        return {
            'stall': self.stall,
            'waits': self.waits,
            'issued': self.issued,
            'progress_events': self.progress_events,
            'no_progress_events': self.no_progress_events,
            'wait_events': self.wait_events,
            'progress_ratio': round(progress_ratio, 6),
            'tabu_actions': len(self.failed_actions),
            'evidence_bounded_retries': len(self.evidence_retry_fingerprints),
            'verified_checkpoints': len(self.checkpoints),
            'backtrack_events': self.backtrack_events,
            'last_verified_checkpoint': dict(self.checkpoints[-1]) if self.checkpoints else None,
            'latency_samples': len(xs),
            'latency_p50_s': round(statistics.median(xs), 3) if xs else 0.0,
            'latency_max_s': round(max(xs), 3) if xs else 0.0,
            'mode': self.decision()['mode'],
            'reason': self.decision()['reason'],
        }

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
        self.pending_action = None
        self.latencies = deque(maxlen=32)
        self.stall = 0
        self.waits = 0
        self.issued = 0
        self.progress_events = 0
        self.no_progress_events = 0
        self.wait_events = 0

    def before_action(self, command, target=None):
        fp = action_fingerprint(command,target)
        if fp in self.failed_actions:
            return {'allow': False, 'mode': 'replan', 'reason': 'tabu_failed_action',
                    'fingerprint': fp}
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

    def reset(self):
        self.waits = 0
        self.stall = 0
        self.latencies.clear()
        self.pending_action = None
        self.failed_actions.clear()
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
            'latency_samples': len(xs),
            'latency_p50_s': round(statistics.median(xs), 3) if xs else 0.0,
            'latency_max_s': round(max(xs), 3) if xs else 0.0,
            'mode': self.decision()['mode'],
            'reason': self.decision()['reason'],
        }

"""Offline only: no transport, BACnet mapping or production-approved limits.
Expiry requires tick(); this is not a physical fail-safe or background timer.
"""
from copy import deepcopy
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Policy:
    minimum: float
    maximum: float
    max_duration: float

class CommandSimulation:
    FEATURES = frozenset(('heating_large', 'heating_small', 'quiet_large', 'haze_clear_large'))
    VENTILATION = frozenset(('quiet_large', 'haze_clear_large'))

    @staticmethod
    def number(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)

    def __init__(self, policies, clock, checkpoint=None):
        if not set(policies) <= self.FEATURES:
            raise ValueError('Unknown feature')
        for p in policies.values():
            if not all(self.number(v) for v in (p.minimum, p.maximum, p.max_duration)) or p.minimum > p.maximum or p.max_duration <= 0:
                raise ValueError('Invalid limits')
        self.policies, self.clock = dict(policies), clock
        self.active, self.journal = {}, []
        self.connected = self.safety_clear = True
        self.last_time = None
        if checkpoint is not None:
            if checkpoint.get('mode') != 'simulation':
                raise ValueError('Not a simulation checkpoint')
            for session in checkpoint.get('active', {}).values():
                self.record('restart_cancelled', session=session)

    def now(self):
        t = self.clock()
        if not self.number(t) or (self.last_time is not None and t < self.last_time):
            raise ValueError('Monotonic finite clock required')
        self.last_time = t
        return t

    def record(self, event, **data):
        self.journal.append(dict(event=event, at=self.now(), mode='simulation', **deepcopy(data)))

    def start(self, feature, value, duration):
        self.tick()
        p = self.policies.get(feature)
        reason = None
        if p is None:
            reason = 'not_allowlisted'
        elif not self.connected or not self.safety_clear:
            reason = 'interlock'
        elif not self.number(value) or not p.minimum <= value <= p.maximum:
            reason = 'value_out_of_bounds'
        elif not self.number(duration) or not 0 < duration <= p.max_duration:
            reason = 'duration_out_of_bounds'
        elif feature in self.active or (feature in self.VENTILATION and self.VENTILATION & self.active.keys()):
            reason = 'conflicting_session'
        if reason:
            self.record('rejected', feature=feature, reason=reason)
            raise ValueError(reason)
        session = dict(feature=feature, value=value, expires_at=self.now()+duration)
        self.active[feature] = session
        self.record('started', session=session)
        return deepcopy(session)

    def stop(self, feature, reason='manual'):
        session = self.active.pop(feature, None)
        if session is not None:
            self.record('released', session=session, reason=reason,
                        result='simulated_only_no_physical_confirmation')
        return session is not None

    def tick(self):
        t = self.now()
        for feature, session in list(self.active.items()):
            if t >= session['expires_at']:
                self.stop(feature, 'expired')
        return deepcopy(self.active)

    def interlocks(self, *, connected, safety_clear):
        if type(connected) is not bool or type(safety_clear) is not bool:
            raise ValueError('Explicit boolean interlocks required')
        self.connected, self.safety_clear = connected, safety_clear
        if not connected or not safety_clear:
            for feature in list(self.active):
                self.stop(feature, 'communication_lost' if not connected else 'safety')
        self.record('interlocks', connected=connected, safety_clear=safety_clear)

    def snapshot(self):
        self.tick()
        return deepcopy(dict(mode='simulation', real_writes_enabled=False,
                             active=self.active, journal=self.journal))

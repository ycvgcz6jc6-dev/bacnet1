"""Read-only evidence collection. This module never authorizes or sends commands."""
from datetime import datetime, timezone

AUDIT_TYPES = frozenset(
    f'{family}-{suffix}'
    for family in ('analog', 'binary', 'multi-state')
    for suffix in ('output', 'value')
)
AUDIT_PROPERTIES = ('priorityArray', 'relinquishDefault')


def audit_properties(kind):
    return AUDIT_PROPERTIES if kind in AUDIT_TYPES else ()


def evidence(record, now=None, max_age=1860):
    """Expose raw evidence, distinguishing missing, failed, and stale reads.

    A readable priority array does not prove write permission or safe operation.
    No priority, state meaning, room assignment, or allowed command is inferred.
    """
    now = now or datetime.now(timezone.utc)
    properties = {}
    for prop in audit_properties(record['object_type']):
        read = record.get('metadata_reads', {}).get(prop, {})
        stamp = read.get('last_success')
        age = None
        try:
            parsed = datetime.fromisoformat(stamp)
            if parsed.tzinfo is not None:
                age = (now - parsed).total_seconds()
        except (TypeError, ValueError):
            pass
        present = prop in record.get('metadata', {})
        fresh = read.get('status') == 'read' and present and age is not None and 0 <= age <= max_age
        properties[prop] = {
            'read_status': read.get('status', 'not_collected'),
            'fresh': fresh,
            'last_success': stamp,
            'raw': record.get('metadata', {}).get(prop),
            'error': read.get('error'),
        }
    return {
        'properties': properties,
        'evidence_complete': bool(properties) and all(p['fresh'] for p in properties.values()),
        'write_permission': 'unverified',
        'allowed': False,
        'write_priority': None,
        'reason': 'Audit only; explicit point approval and CPO safety review required',
    }

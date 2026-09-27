import unittest
from datetime import datetime, timezone, timedelta
from command_audit import audit_properties, evidence
from phase2 import properties_for


class CommandAuditTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.rec = {'object_type': 'multi-state-value',
                    'metadata': {'priorityArray': [{'null': []}]*16, 'relinquishDefault': 2},
                    'metadata_reads': {p: {'status': 'read', 'last_success': self.now.isoformat()}
                                       for p in audit_properties('multi-state-value')}}

    def test_complete_evidence_never_authorizes(self):
        result = evidence(self.rec, self.now)
        self.assertTrue(result['evidence_complete'])
        self.assertFalse(result['allowed'])
        self.assertIsNone(result['write_priority'])
        self.assertEqual(result['write_permission'], 'unverified')
        self.assertEqual(result['properties']['priorityArray']['raw'], self.rec['metadata']['priorityArray'])

    def test_missing_failed_and_stale_are_not_complete(self):
        for prop in audit_properties('multi-state-value'):
            original = self.rec['metadata_reads'][prop]
            for entry in ({}, {'status': 'unavailable', 'last_success': self.now.isoformat()},
                          {'status': 'read', 'last_success': (self.now-timedelta(hours=1)).isoformat()},
                          {'status': 'read', 'last_success': (self.now+timedelta(hours=1)).isoformat()}):
                self.rec['metadata_reads'][prop] = entry
                self.assertFalse(evidence(self.rec, self.now)['evidence_complete'])
            self.rec['metadata_reads'][prop] = original

    def test_missing_value_despite_read_status(self):
        del self.rec['metadata']['priorityArray']
        self.assertFalse(evidence(self.rec, self.now)['evidence_complete'])

    def test_properties_are_added_without_removing_legacy_metadata(self):
        for kind in ('analog-output', 'binary-output', 'multi-state-output',
                     'analog-value', 'binary-value', 'multi-state-value'):
            self.assertIn('priorityArray', properties_for(kind))
            self.assertIn('relinquishDefault', properties_for(kind))
            self.assertIn('statusFlags', properties_for(kind))
            self.assertIn('objectName', properties_for(kind))
        for kind in ('analog-input', 'binary-input', 'multi-state-input', 'file', 'device', 'schedule'):
            self.assertEqual(audit_properties(kind), ())
            self.assertNotIn('priorityArray', properties_for(kind))

    def test_inputs_never_become_allowed(self):
        self.rec['object_type'] = 'binary-input'
        result = evidence(self.rec, self.now)
        self.assertFalse(result['allowed'])
        self.assertFalse(result['evidence_complete'])


if __name__ == '__main__':
    unittest.main()

import unittest
from command_simulation import CommandSimulation, Policy

class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.t = 100
        # Synthetic fixture, NOT approved building limits.
        self.p = {name: Policy(1, 10, 60) for name in CommandSimulation.FEATURES}
        self.e = CommandSimulation(self.p, lambda: self.t)

    def test_bounds_and_allowlist(self):
        for args in [('fire',5,10),('quiet_large',11,10),('quiet_large',float('nan'),10),
                     ('quiet_large',True,10),('quiet_large',5,0),('quiet_large',5,61),
                     ('quiet_large',5,float('inf'))]:
            with self.assertRaises(ValueError): self.e.start(*args)
        self.assertFalse(self.e.active)
        self.assertEqual(len(self.e.journal),7)

    def test_expiration(self):
        self.e.start('quiet_large',5,10)
        self.t=109
        self.assertTrue(self.e.tick())
        self.t=110
        self.assertFalse(self.e.tick())
        self.assertEqual(self.e.journal[-1]['reason'],'expired')
        self.assertIn('no_physical_confirmation',self.e.journal[-1]['result'])

    def test_conflicts_and_independent_heating(self):
        self.e.start('quiet_large',5,10)
        with self.assertRaises(ValueError): self.e.start('haze_clear_large',8,10)
        for f in ('heating_large','heating_small'): self.e.start(f,5,10)
        self.assertEqual(len(self.e.active),3)
        self.e.stop('quiet_large')
        self.e.start('haze_clear_large',8,10)

    def test_interlocks(self):
        for connected,safe in ((False,True),(True,False)):
            self.e.interlocks(connected=True,safety_clear=True)
            self.e.start('heating_large',5,10)
            self.e.interlocks(connected=connected,safety_clear=safe)
            self.assertFalse(self.e.active)
            with self.assertRaises(ValueError): self.e.start('heating_large',5,10)
            self.e.interlocks(connected=True,safety_clear=True)
            self.assertFalse(self.e.active)

    def test_restart_no_replay(self):
        self.e.start('haze_clear_large',9,20)
        r=CommandSimulation(self.p,lambda:self.t,self.e.snapshot())
        self.assertFalse(r.active)
        self.assertEqual(r.journal[0]['event'],'restart_cancelled')
        self.assertFalse(r.snapshot()['real_writes_enabled'])

    def test_snapshot_and_idempotence(self):
        self.e.start('quiet_large',5,10)
        s=self.e.snapshot(); s['active'].clear()
        self.assertTrue(self.e.active)
        self.assertTrue(self.e.stop('quiet_large'))
        self.assertFalse(self.e.stop('quiet_large'))

    def test_invalid_configuration(self):
        with self.assertRaises(ValueError): CommandSimulation({'quiet_large':Policy(10,1,60)},lambda:0)
        with self.assertRaises(ValueError): CommandSimulation(self.p,lambda:0,{'mode':'live'})
        self.e.tick(); self.t-=1
        with self.assertRaises(ValueError): self.e.tick()

if __name__=='__main__': unittest.main()

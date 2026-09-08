"""Runs only against ephemeral CI Postgres, never production."""
import concurrent.futures,json,os,subprocess,unittest

def sql(query):
    if os.environ.get("ARBM_TEST_DATABASE")!="1" or os.environ.get("PGDATABASE")!="mesh_test":
        raise RuntimeError("ephemeral_test_database_required")
    r=subprocess.run(["psql","-X","-qAt","-v","ON_ERROR_STOP=1","-c",query],capture_output=True,text=True,check=True)
    return r.stdout.strip()
def acquire():return json.loads(sql("select public.arbm_mesh_acquire('mistral',1000)"))
class SharedTests(unittest.TestCase):
    def setUp(self):
        sql("update arbm_mesh_private.provider_state set lease_id=null,lease_until=null,cooldown_until=null,day_tokens=0,month_tokens=0,daily_internal_limit=3000000,monthly_internal_limit=93000000,safety_reserve=10000,day_start=(now() at time zone 'UTC')::date,month_start=date_trunc('month',now() at time zone 'UTC')::date where provider='mistral'")
    def complete(self,lease,health='healthy',usage='10',retry=0):
        return json.loads(sql(f"select public.arbm_mesh_complete('mistral','{lease}', '{health}',{usage},{retry})"))
    def test_concurrent_atomic_acquire(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda _:acquire(),range(8)))
        self.assertEqual(sum(r['allowed'] for r in results),1)
        self.assertEqual(sql("select day_tokens from arbm_mesh_private.provider_state where provider='mistral'"),'1000')
    def test_cooldown_and_recovery(self):
        lease=acquire()['lease_id'];self.complete(lease,'cooling_down','NULL',120)
        self.assertFalse(acquire()['allowed'])
        sql("update arbm_mesh_private.provider_state set cooldown_until=now()-interval '1 second' where provider='mistral'")
        self.assertTrue(acquire()['allowed'])
    def test_expired_lease_retains_reservation_and_rejects_late_completion(self):
        first=acquire()['lease_id'];sql("update arbm_mesh_private.provider_state set lease_until=now()-interval '1 second' where provider='mistral'")
        second=acquire()['lease_id'];self.assertNotEqual(first,second)
        self.assertFalse(self.complete(first)['accepted'])
        self.assertEqual(sql("select day_tokens from arbm_mesh_private.provider_state where provider='mistral'"),'2000')
    def test_duplicate_completion_does_not_refund_twice(self):
        lease=acquire()['lease_id'];self.assertTrue(self.complete(lease)['accepted']);self.assertFalse(self.complete(lease)['accepted'])
        self.assertEqual(sql("select day_tokens from arbm_mesh_private.provider_state where provider='mistral'"),'10')
    def test_unknown_usage_never_refunds(self):
        lease=acquire()['lease_id'];self.complete(lease,usage='NULL')
        self.assertEqual(sql("select day_tokens from arbm_mesh_private.provider_state where provider='mistral'"),'1000')
    def test_budget_reserve_fail_closed(self):
        sql("update arbm_mesh_private.provider_state set daily_internal_limit=10500 where provider='mistral'")
        self.assertEqual(acquire()['reason'],'quota_exhausted')
    def test_month_exhaustion_and_reset(self):
        sql("update arbm_mesh_private.provider_state set month_tokens=93000000 where provider='mistral'")
        self.assertFalse(acquire()['allowed'])
        sql("update arbm_mesh_private.provider_state set month_start='2000-01-01' where provider='mistral'")
        self.assertTrue(acquire()['allowed'])
    def test_cross_midnight_usage_is_charged_to_new_window(self):
        lease=acquire()['lease_id'];sql("update arbm_mesh_private.provider_state set day_start='2000-01-01',month_start='2000-01-01' where provider='mistral'")
        self.complete(lease,usage='100')
        self.assertEqual(sql("select day_tokens || ':' || month_tokens from arbm_mesh_private.provider_state where provider='mistral'"),'100:100')
    def test_public_and_authenticated_have_no_access(self):
        for role in ('anon','authenticated'):
            self.assertEqual(sql(f"select has_function_privilege('{role}','public.arbm_mesh_acquire(text,bigint)','execute')"),'f')
            self.assertEqual(sql(f"select has_table_privilege('{role}','arbm_mesh_private.provider_state','select')"),'f')
        self.assertEqual(sql("select relrowsecurity from pg_class where oid='arbm_mesh_private.provider_state'::regclass"),'t')
if __name__=='__main__':unittest.main()

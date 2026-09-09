#!/usr/bin/env bash
set -euo pipefail
createdb v3test
psql -d v3test -v ON_ERROR_STOP=1 <<'SQL'
create schema ar_system;
create table ar_system.jobs(
  tenant_id text not null,
  job_id bigint primary key,
  status text not null,
  payload jsonb not null default '{}'::jsonb
);
insert into ar_system.jobs
select 'tenant-'||g,g,'queued',jsonb_build_object('n',g)
from generate_series(1,10000) g;
SQL
docker run --rm --network host -e PGPASSWORD=postgres -v "$PWD:/work" postgres:17 \
  pg_dump -h 127.0.0.1 -U postgres -Fc -d v3test -f /work/pre-migration.dump
psql -d v3test -v ON_ERROR_STOP=1 -c \
  "alter table ar_system.jobs add column priority integer not null default 0"
psql -d v3test -v ON_ERROR_STOP=1 -c \
  "insert into ar_system.jobs(tenant_id,job_id,status,payload,priority) select 'canary-'||g,10000+g,'queued','{}',7 from generate_series(1,100) g"
test "$(psql -d v3test -Atc "select count(*) from ar_system.jobs where priority=7")" = "100"psql -d v3test -v ON_ERROR_STOP=1 -c \
  "insert into ar_system.jobs(tenant_id,job_id,status,payload) values('old-client',20001,'queued','{}')"
psql -d v3test -v ON_ERROR_STOP=1 -c \
  "insert into ar_system.jobs(tenant_id,job_id,status,payload,priority) values('new-client',20002,'queued','{}',9)"
test "$(psql -d v3test -Atc "select count(*) from ar_system.jobs where job_id in (20001,20002)")" = "2"
createdb rollback_v3
docker run --rm --network host -e PGPASSWORD=postgres -v "$PWD:/work" postgres:17 \
  pg_restore -h 127.0.0.1 -U postgres --exit-on-error -d rollback_v3 /work/pre-migration.dump
test "$(psql -d rollback_v3 -Atc "select count(*) from ar_system.jobs")" = "10000"
test "$(psql -d rollback_v3 -Atc "select count(*) from information_schema.columns where table_schema='ar_system' and table_name='jobs' and column_name='priority'")" = "0"
cat > bench.sql <<'EOF'
\set tenant random(1,10000)
select status from ar_system.jobs where job_id = :tenant;
EOF
docker run --rm --network host -e PGPASSWORD=postgres -v "$PWD:/work" postgres:17 \
  pgbench -h 127.0.0.1 -U postgres -d v3test -n -c 32 -j 4 -t 313 -f /work/bench.sql | tee pgbench.txt
grep -q 'number of failed transactions: 0' pgbench.txt
grep -q 'tps = ' pgbench.txt
node --test test_mesh_resilience.mjs | tee failure.txt
grep -q '# fail 0' failure.txt
grep -q 'N-1' failure.txttps=$(awk '/^tps =/{print $3; exit}' pgbench.txt)
latency=$(awk '/latency average =/{print $4; exit}' pgbench.txt)
cat > top3-v3-proof.json <<EOF
{"schema":"arbm-top3-v3-migration-load-failure-v1","result":"PASS","baseline_tenants":10000,"canary_rows":100,"mixed_version":true,"rollback_verified":true,"load_transactions":10016,"failed_transactions":0,"tps":${tps:-0},"latency_ms":${latency:-0},"failure_injection":"PASS","zero_spend_mode":"HARD"}
EOF
cat top3-v3-proof.json
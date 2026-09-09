create schema if not exists arbm_sist_top3;
create table arbm_sist_top3.tenant_jobs(
  job_id text primary key,
  tenant_id text not null,
  idempotency_key text not null,
  cell_id text not null,
  residency_region text not null,
  payload jsonb not null default '{}'::jsonb,
  unique(tenant_id,idempotency_key)
);
create table arbm_sist_top3.budget_accounts(
  tenant_id text not null,
  budget_id text not null,
  available numeric(18,6) not null default 0,
  reserved numeric(18,6) not null default 0,
  primary key(tenant_id,budget_id),
  check(available>=0),check(reserved>=0)
);
insert into arbm_sist_top3.tenant_jobs
select 'job-'||g,'tenant-'||lpad(((g-1)%10000+1)::text,5,'0'),'idem-'||lpad(g::text,8,'0'),'cell-'||((g-1)%8+1),'sa-east-1',jsonb_build_object('seq',g)
from generate_series(1,20000) g;
insert into arbm_sist_top3.budget_accounts
select 'tenant-'||lpad(g::text,5,'0'),'main',1000,0
from generate_series(1,10000) g;

alter table arbm_sist_top3.tenant_jobs enable row level security;
alter table arbm_sist_top3.tenant_jobs force row level security;
alter table arbm_sist_top3.budget_accounts enable row level security;
alter table arbm_sist_top3.budget_accounts force row level security;

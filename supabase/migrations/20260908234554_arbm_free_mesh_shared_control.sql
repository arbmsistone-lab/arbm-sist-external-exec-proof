-- Private, service-role-only health leases and internal token reservations.
create schema if not exists arbm_mesh_private;
revoke all on schema arbm_mesh_private from public, anon, authenticated;
create table if not exists arbm_mesh_private.provider_state (
 provider text primary key check (provider in ('lightning','groq','google','mistral')),
 health text not null default 'healthy', cooldown_until timestamptz,
 retry_after integer, last_success timestamptz, last_failure timestamptz,
 failure_count integer not null default 0,
 lease_id uuid, lease_until timestamptz, reserved_tokens bigint not null default 0,
 day_start date not null default (now() at time zone 'UTC')::date,
 month_start date not null default date_trunc('month',now() at time zone 'UTC')::date,
 day_tokens bigint not null default 0, month_tokens bigint not null default 0,
 daily_internal_limit bigint not null default 3000000,
 monthly_internal_limit bigint not null default 93000000,
 safety_reserve bigint not null default 10000,
 measured_tokens bigint not null default 0, unknown_usage_count bigint not null default 0,
 updated_at timestamptz not null default now()
);
alter table arbm_mesh_private.provider_state enable row level security;
revoke all on arbm_mesh_private.provider_state from public,anon,authenticated;
insert into arbm_mesh_private.provider_state(provider) values ('lightning'),('groq'),('google'),('mistral') on conflict do nothing;

create or replace function public.arbm_mesh_acquire(p_provider text,p_reserve bigint)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare s arbm_mesh_private.provider_state%rowtype; t timestamptz:=clock_timestamp(); lid uuid;
begin
 if p_reserve is null or p_reserve<1 or p_reserve>1000000 then return jsonb_build_object('allowed',false,'reason','invalid_reservation'); end if;
 select * into s from arbm_mesh_private.provider_state where provider=p_provider for update;
 if not found then return jsonb_build_object('allowed',false,'reason','unknown_provider'); end if;
 if s.lease_until>t then return jsonb_build_object('allowed',false,'reason','in_flight'); end if;
 if s.cooldown_until>t then return jsonb_build_object('allowed',false,'reason',s.health,'cooldown_until',s.cooldown_until); end if;
 -- An expired lease retains its entire reservation: a lost response must not refund usage.
 if s.day_start<>(t at time zone 'UTC')::date then s.day_tokens:=0; s.day_start:=(t at time zone 'UTC')::date; end if;
 if s.month_start<>date_trunc('month',t at time zone 'UTC')::date then s.month_tokens:=0; s.month_start:=date_trunc('month',t at time zone 'UTC')::date; end if;
 if s.day_tokens+p_reserve+s.safety_reserve>s.daily_internal_limit or s.month_tokens+p_reserve+s.safety_reserve>s.monthly_internal_limit then
  update arbm_mesh_private.provider_state set health='quota_exhausted',day_start=s.day_start,month_start=s.month_start,day_tokens=s.day_tokens,month_tokens=s.month_tokens,updated_at=t where provider=p_provider;
  return jsonb_build_object('allowed',false,'reason','quota_exhausted');
 end if;
 lid:=gen_random_uuid();
 update arbm_mesh_private.provider_state set lease_id=lid,lease_until=t+interval '90 seconds',reserved_tokens=p_reserve,day_start=s.day_start,month_start=s.month_start,day_tokens=s.day_tokens+p_reserve,month_tokens=s.month_tokens+p_reserve,health='healthy',cooldown_until=null,updated_at=t where provider=p_provider;
 return jsonb_build_object('allowed',true,'lease_id',lid,'lease_until',t+interval '90 seconds','budget_kind','internal_policy_not_account_allowance','daily_remaining',s.daily_internal_limit-s.day_tokens-p_reserve-s.safety_reserve,'monthly_remaining',s.monthly_internal_limit-s.month_tokens-p_reserve-s.safety_reserve);
end $$;

create or replace function public.arbm_mesh_complete(p_provider text,p_lease uuid,p_health text,p_usage bigint,p_retry_seconds integer)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare s arbm_mesh_private.provider_state%rowtype; t timestamptz:=clock_timestamp(); refund bigint:=0;
begin
 if p_health not in ('healthy','cooling_down','quota_exhausted','auth_failed','transient_failure') or p_retry_seconds is null or p_retry_seconds<0 or p_retry_seconds>2678400 or (p_usage is not null and p_usage<0) then return jsonb_build_object('accepted',false,'reason','invalid_completion'); end if;
 select * into s from arbm_mesh_private.provider_state where provider=p_provider for update;
 if not found or s.lease_id is distinct from p_lease or s.lease_until<=t then return jsonb_build_object('accepted',false,'reason','stale_lease'); end if;
 if p_usage is not null then refund:=s.reserved_tokens-p_usage; end if;
 update arbm_mesh_private.provider_state set
 day_tokens=case when day_start<>(t at time zone 'UTC')::date then coalesce(p_usage,s.reserved_tokens) else greatest(0,day_tokens-refund) end,
 month_tokens=case when month_start<>date_trunc('month',t at time zone 'UTC')::date then coalesce(p_usage,s.reserved_tokens) else greatest(0,month_tokens-refund) end,
 day_start=(t at time zone 'UTC')::date,month_start=date_trunc('month',t at time zone 'UTC')::date,
 measured_tokens=measured_tokens+coalesce(p_usage,0),unknown_usage_count=unknown_usage_count+case when p_usage is null then 1 else 0 end,
 lease_id=null,lease_until=null,reserved_tokens=0,health=p_health,
 retry_after=p_retry_seconds,cooldown_until=case when p_retry_seconds>0 then t+make_interval(secs=>p_retry_seconds) else null end,
 last_success=case when p_health='healthy' then t else last_success end,
 last_failure=case when p_health<>'healthy' then t else last_failure end,
 failure_count=case when p_health='healthy' then 0 else failure_count+1 end,updated_at=t
 where provider=p_provider;
 return jsonb_build_object('accepted',true);
end $$;
revoke all on function public.arbm_mesh_acquire(text,bigint) from public,anon,authenticated;
revoke all on function public.arbm_mesh_complete(text,uuid,text,bigint,integer) from public,anon,authenticated;
grant execute on function public.arbm_mesh_acquire(text,bigint) to service_role;
grant execute on function public.arbm_mesh_complete(text,uuid,text,bigint,integer) to service_role;
comment on table arbm_mesh_private.provider_state is 'Internal UTC policy counters only; NOT provider account quota evidence. No keys, prompts or generated commands stored.';

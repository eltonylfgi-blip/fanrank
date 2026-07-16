-- FanRank v16: deterministic profile languages and private milestone-alert preferences.
-- Delivery deliberately remains blocked until an email provider, domain, confirmation
-- and unsubscribe flow are verified end to end.

begin;

alter table public.fr_sections
  add column default_language text not null default 'auto';

alter table public.fr_sections
  add constraint fr_sections_default_language_check
  check (default_language in ('auto', 'es', 'en'));

update public.fr_sections
set default_language = 'es'
where slug in ('rubius', 'orslok', 'ibai', 'cuaderno-madre');

create index if not exists fr_submissions_canonical_idea_idx
  on public.fr_submissions(canonical_idea_id)
  where canonical_idea_id is not null;

create table fanrank_private.fr_milestone_subscriptions (
  id uuid primary key default extensions.gen_random_uuid(),
  submission_id bigint not null unique
    references public.fr_submissions(id) on delete cascade,
  user_id uuid references auth.users(id) on delete set null,
  email_normalized text not null
    check (char_length(email_normalized) between 3 and 254),
  email_hash text not null check (email_hash ~ '^[0-9a-f]{64}$'),
  milestones text[] not null,
  language text not null check (language in ('es', 'en')),
  status text not null default 'pending_provider'
    check (status in (
      'pending_provider', 'pending_confirmation', 'active',
      'unsubscribed', 'bounced', 'complained'
    )),
  consent_version text not null default 'milestones_v1'
    check (consent_version = 'milestones_v1'),
  consent_at timestamptz not null default current_timestamp,
  confirmed_at timestamptz,
  unsubscribed_at timestamptz,
  created_at timestamptz not null default current_timestamp,
  updated_at timestamptz not null default current_timestamp,
  constraint fr_milestone_subscriptions_milestones_check check (
    cardinality(milestones) between 1 and 5
    and milestones <@ array[
      'published', 'hearts_100', 'above_average', 'ai_90', 'official_star'
    ]::text[]
  )
);

create table fanrank_private.fr_milestone_outbox (
  id bigint generated always as identity primary key,
  subscription_id uuid not null
    references fanrank_private.fr_milestone_subscriptions(id) on delete cascade,
  idea_id integer not null references public.fr_ideas(id) on delete cascade,
  milestone text not null check (milestone in (
    'published', 'hearts_100', 'above_average', 'ai_90', 'official_star'
  )),
  snapshot jsonb not null default '{}'::jsonb
    check (jsonb_typeof(snapshot) = 'object'),
  status text not null default 'blocked_provider'
    check (status in (
      'blocked_provider', 'blocked_unconfirmed', 'pending', 'processing',
      'retry', 'sent', 'dead', 'cancelled'
    )),
  attempts smallint not null default 0 check (attempts between 0 and 20),
  available_at timestamptz not null default current_timestamp,
  locked_at timestamptz,
  sent_at timestamptz,
  provider_message_id text check (provider_message_id is null or char_length(provider_message_id) <= 255),
  last_error text check (last_error is null or char_length(last_error) <= 500),
  created_at timestamptz not null default current_timestamp,
  updated_at timestamptz not null default current_timestamp,
  unique (subscription_id, idea_id, milestone)
);

create index fr_milestone_outbox_work_idx
  on fanrank_private.fr_milestone_outbox(status, available_at, id);

create table fanrank_private.fr_milestone_optin_events (
  id bigint generated always as identity primary key,
  receipt_hash text not null check (receipt_hash ~ '^[0-9a-f]{64}$'),
  email_hash text not null check (email_hash ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default current_timestamp
);

create index fr_milestone_optin_events_email_idx
  on fanrank_private.fr_milestone_optin_events(email_hash, created_at desc);

alter table fanrank_private.fr_milestone_subscriptions enable row level security;
alter table fanrank_private.fr_milestone_subscriptions force row level security;
alter table fanrank_private.fr_milestone_outbox enable row level security;
alter table fanrank_private.fr_milestone_outbox force row level security;
alter table fanrank_private.fr_milestone_optin_events enable row level security;
alter table fanrank_private.fr_milestone_optin_events force row level security;

revoke all on fanrank_private.fr_milestone_subscriptions
  from public, anon, authenticated, service_role;
revoke all on fanrank_private.fr_milestone_outbox
  from public, anon, authenticated, service_role;
revoke all on fanrank_private.fr_milestone_optin_events
  from public, anon, authenticated, service_role;
revoke all on sequence fanrank_private.fr_milestone_outbox_id_seq
  from public, anon, authenticated, service_role;
revoke all on sequence fanrank_private.fr_milestone_optin_events_id_seq
  from public, anon, authenticated, service_role;

create or replace function fanrank_private.fr_enqueue_milestone(
  p_subscription_id uuid,
  p_idea_id integer,
  p_milestone text,
  p_snapshot jsonb
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_delivery_status text;
begin
  select case subscription.status
    when 'pending_provider' then 'blocked_provider'
    when 'pending_confirmation' then 'blocked_unconfirmed'
    when 'active' then 'pending'
    else 'cancelled'
  end
  into v_delivery_status
  from fanrank_private.fr_milestone_subscriptions as subscription
  where subscription.id = p_subscription_id;

  if v_delivery_status is null or v_delivery_status = 'cancelled' then
    return;
  end if;

  insert into fanrank_private.fr_milestone_outbox (
    subscription_id, idea_id, milestone, snapshot, status
  ) values (
    p_subscription_id, p_idea_id, p_milestone, p_snapshot, v_delivery_status
  )
  on conflict (subscription_id, idea_id, milestone) do update
  set snapshot = excluded.snapshot,
      status = case
        when fanrank_private.fr_milestone_outbox.status = 'cancelled'
          then excluded.status
        else fanrank_private.fr_milestone_outbox.status
      end,
      updated_at = current_timestamp;
end;
$$;

revoke all on function fanrank_private.fr_enqueue_milestone(uuid, integer, text, jsonb)
  from public, anon, authenticated, service_role;

create or replace function fanrank_private.fr_queue_submission_milestones(
  p_submission_id bigint
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_subscription fanrank_private.fr_milestone_subscriptions%rowtype;
  v_submission public.fr_submissions%rowtype;
  v_idea public.fr_ideas%rowtype;
  v_peer_count integer := 0;
  v_peer_average numeric := 0;
  v_snapshot jsonb;
begin
  select * into v_subscription
  from fanrank_private.fr_milestone_subscriptions
  where submission_id = p_submission_id
    and status not in ('unsubscribed', 'bounced', 'complained');
  if not found then return; end if;

  select * into v_submission
  from public.fr_submissions
  where id = p_submission_id
    and canonical_idea_id is not null;
  if not found then return; end if;

  select * into v_idea
  from public.fr_ideas
  where id = v_submission.canonical_idea_id;
  if not found then return; end if;

  select count(*)::integer, coalesce(avg(peer.web_votes), 0)
  into v_peer_count, v_peer_average
  from public.fr_ideas as peer
  where peer.section = v_idea.section
    and peer.approved = true
    and peer.id <> v_idea.id;

  v_snapshot := pg_catalog.jsonb_build_object(
    'web_votes', v_idea.web_votes,
    'ai_score', v_idea.ai_score,
    'owner_star_value', v_idea.owner_star_value,
    'team_star_support_count', v_idea.team_star_support_count,
    'peer_average', pg_catalog.round(v_peer_average, 2),
    'captured_at', current_timestamp
  );

  if 'published' = any(v_subscription.milestones)
     and v_idea.approved = true
     and v_submission.status in ('published', 'merged') then
    perform fanrank_private.fr_enqueue_milestone(
      v_subscription.id, v_idea.id, 'published', v_snapshot
    );
  end if;

  if 'hearts_100' = any(v_subscription.milestones)
     and v_idea.approved = true and v_idea.web_votes >= 100 then
    perform fanrank_private.fr_enqueue_milestone(
      v_subscription.id, v_idea.id, 'hearts_100', v_snapshot
    );
  end if;

  if 'above_average' = any(v_subscription.milestones)
     and v_idea.approved = true
     and v_idea.web_votes >= 5
     and v_peer_count >= 2
     and v_idea.web_votes > v_peer_average then
    perform fanrank_private.fr_enqueue_milestone(
      v_subscription.id, v_idea.id, 'above_average', v_snapshot
    );
  end if;

  if 'ai_90' = any(v_subscription.milestones)
     and v_idea.approved = true and v_idea.ai_score >= 90 then
    perform fanrank_private.fr_enqueue_milestone(
      v_subscription.id, v_idea.id, 'ai_90', v_snapshot
    );
  end if;

  if 'official_star' = any(v_subscription.milestones)
     and v_idea.approved = true
     and (v_idea.owner_star_value > 0 or v_idea.team_star_support_count > 0) then
    perform fanrank_private.fr_enqueue_milestone(
      v_subscription.id, v_idea.id, 'official_star', v_snapshot
    );
  end if;
end;
$$;

revoke all on function fanrank_private.fr_queue_submission_milestones(bigint)
  from public, anon, authenticated, service_role;

create or replace function public.fr_register_milestone_subscription(
  p_receipt_hash text,
  p_email text,
  p_milestones text[],
  p_language text
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_submission_id bigint;
  v_user_id uuid;
  v_email text := pg_catalog.lower(pg_catalog.btrim(coalesce(p_email, '')));
  v_email_hash text;
  v_milestones text[];
  v_subscription_id uuid;
  v_recent_10m integer;
  v_recent_day integer;
begin
  if p_receipt_hash is null or p_receipt_hash !~ '^[0-9a-f]{64}$'
     or char_length(v_email) > 254
     or v_email !~ '^[^[:space:]@]+@[^[:space:]@]+[.][^[:space:]@]+$'
     or p_language not in ('es', 'en')
     or p_milestones is null
     or exists (
       select 1 from pg_catalog.unnest(p_milestones) as milestone
       where milestone not in ('published', 'hearts_100', 'above_average', 'ai_90', 'official_star')
     ) then
    return false;
  end if;

  select pg_catalog.array_agg(distinct milestone order by milestone)
  into v_milestones
  from pg_catalog.unnest(p_milestones) as milestone;
  if cardinality(v_milestones) not between 1 and 5 then return false; end if;

  v_email_hash := pg_catalog.encode(extensions.digest(v_email, 'sha256'), 'hex');
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(v_email_hash, 0));

  delete from fanrank_private.fr_milestone_optin_events
  where created_at < current_timestamp - interval '2 days';

  select count(*) filter (where created_at >= current_timestamp - interval '10 minutes'),
         count(*) filter (where created_at >= current_timestamp - interval '1 day')
  into v_recent_10m, v_recent_day
  from fanrank_private.fr_milestone_optin_events
  where email_hash = v_email_hash;

  if v_recent_10m >= 3 or v_recent_day >= 10 then return false; end if;

  insert into fanrank_private.fr_milestone_optin_events(receipt_hash, email_hash)
  values (p_receipt_hash, v_email_hash);

  select submission.id, submission.user_id
  into v_submission_id, v_user_id
  from public.fr_submissions as submission
  where submission.receipt_hash = p_receipt_hash
  limit 1;
  if not found then return false; end if;

  insert into fanrank_private.fr_milestone_subscriptions (
    submission_id, user_id, email_normalized, email_hash, milestones,
    language, status, consent_at, updated_at
  ) values (
    v_submission_id, v_user_id, v_email, v_email_hash, v_milestones,
    p_language, 'pending_provider', current_timestamp, current_timestamp
  )
  on conflict (submission_id) do update
  set user_id = excluded.user_id,
      email_normalized = excluded.email_normalized,
      email_hash = excluded.email_hash,
      milestones = excluded.milestones,
      language = excluded.language,
      status = 'pending_provider',
      confirmed_at = null,
      unsubscribed_at = null,
      consent_at = current_timestamp,
      updated_at = current_timestamp
  returning id into v_subscription_id;

  update fanrank_private.fr_milestone_outbox
  set status = 'cancelled', updated_at = current_timestamp
  where subscription_id = v_subscription_id
    and not (milestone = any(v_milestones))
    and status in ('blocked_provider', 'blocked_unconfirmed', 'pending', 'retry');

  perform fanrank_private.fr_queue_submission_milestones(v_submission_id);
  return true;
end;
$$;

revoke all on function public.fr_register_milestone_subscription(text, text, text[], text)
  from public, anon, authenticated;
grant execute on function public.fr_register_milestone_subscription(text, text, text[], text) to service_role;

create or replace function fanrank_private.fr_ideas_queue_milestones()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_submission_id bigint;
begin
  for v_submission_id in
    select submission.id
    from public.fr_submissions as submission
    where submission.canonical_idea_id = new.id
  loop
    perform fanrank_private.fr_queue_submission_milestones(v_submission_id);
  end loop;
  return new;
end;
$$;

revoke all on function fanrank_private.fr_ideas_queue_milestones()
  from public, anon, authenticated, service_role;

drop trigger if exists fr_ideas_queue_milestones on public.fr_ideas;
create trigger fr_ideas_queue_milestones
  after update of approved, web_votes, ai_score, owner_star_value, team_star_support_count
  on public.fr_ideas
  for each row execute function fanrank_private.fr_ideas_queue_milestones();

create or replace function fanrank_private.fr_submissions_queue_milestones()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.canonical_idea_id is not null then
    perform fanrank_private.fr_queue_submission_milestones(new.id);
  end if;
  return new;
end;
$$;

revoke all on function fanrank_private.fr_submissions_queue_milestones()
  from public, anon, authenticated, service_role;

drop trigger if exists fr_submissions_queue_milestones on public.fr_submissions;
create trigger fr_submissions_queue_milestones
  after update of canonical_idea_id, status
  on public.fr_submissions
  for each row execute function fanrank_private.fr_submissions_queue_milestones();

create or replace view public.fr_sections_stats
with (security_invoker = true)
as
select
  section_row.slug,
  section_row.name,
  section_row.emoji,
  section_row.kind,
  section_row.tagline,
  section_row.tagline_es,
  count(idea.id)::integer as ideas,
  coalesce(sum(idea.origin_upvotes), 0::bigint)::integer as reddit_upvotes,
  coalesce(sum(idea.web_votes), 0::bigint)::integer as fan_votes,
  section_row.verification_status,
  section_row.tags,
  section_row.featured_rank,
  count(idea.id) filter (where idea.created_at >= pg_catalog.now() - interval '30 days')::integer as recent_ideas,
  section_row.image_path,
  section_row.image_alt,
  section_row.image_source_url,
  section_row.image_credit,
  section_row.image_rights,
  section_row.team_member_star_cap,
  section_row.topic_tier,
  case section_row.topic_tier
    when 'normal' then 5
    when 'pro' then 20
    when 'business' then 100
    when 'plus' then 200
    else 5
  end::integer as topic_limit,
  (
    select count(*)::integer
    from public.fr_profile_topics as topic
    where topic.section = section_row.slug
      and topic.status = 'active'
  ) as topic_active_count,
  section_row.default_language
from public.fr_sections as section_row
left join public.fr_ideas as idea
  on idea.section = section_row.slug
  and idea.approved = true
group by section_row.slug;

revoke all on public.fr_sections_stats from public, anon, authenticated;
grant select on public.fr_sections_stats to anon, authenticated;

alter table public.fr_events
  drop constraint if exists fr_events_event_check;
alter table public.fr_events
  add constraint fr_events_event_check
  check (event in (
    'page_view', 'search', 'profile_open', 'idea_open', 'idea_share', 'vote', 'submission',
    'section_request', 'claim_request', 'suggest_open', 'similar_vote', 'auth_open',
    'auth_link_requested', 'auth_recovery_requested', 'auth_signed_in', 'auth_signed_out',
    'activity_open', 'team_interest', 'team_star', 'team_star_cap', 'team_invite_created',
    'owner_mode_open', 'owner_feedback', 'owner_profile_request', 'profile_image_updated',
    'promotion_interest', 'pro_interest', 'media_added', 'fan_profile_saved', 'fan_profile_open',
    'owner_cta_open', 'topic_filter', 'topic_created', 'topic_archived', 'topic_assigned',
    'alert_optin'
  ));

comment on column public.fr_sections.default_language is
  'Default profile language: explicit links and saved user choice always take precedence; auto follows the browser.';
comment on table fanrank_private.fr_milestone_subscriptions is
  'Private, purpose-specific alert consent. Never exposed to profile teams or public views.';
comment on table fanrank_private.fr_milestone_outbox is
  'Idempotent milestone queue. blocked_provider is intentional until email ownership, delivery and unsubscribe are verified.';

commit;

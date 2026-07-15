-- FanRank v9: practical feedback capture, private media quarantine and fan impact profiles.
-- Attachments require an authenticated session even when public attribution stays anonymous.

begin;

alter table public.fr_submissions
  add column category_requested text not null default 'auto',
  add column category_final text not null default 'pending',
  add column classification_method text not null default 'pending',
  add column ai_training_consent boolean not null default false,
  add column attachment_count smallint not null default 0;

alter table public.fr_submissions
  add constraint fr_submissions_category_requested_check
    check (category_requested in ('auto','bug','idea','accessibility','performance','safety','content','other')),
  add constraint fr_submissions_category_final_check
    check (category_final in ('pending','bug','idea','accessibility','performance','safety','content','other')),
  add constraint fr_submissions_classification_method_check
    check (classification_method in ('pending','user','rules_v1','ai_v1')),
  add constraint fr_submissions_attachment_count_check
    check (attachment_count between 0 and 3);

create or replace function fanrank_private.classify_submission()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_text text := pg_catalog.lower(coalesce(new.title, '') || ' ' || coalesce(new.details, ''));
begin
  if new.category_requested <> 'auto' then
    new.category_final := new.category_requested;
    new.classification_method := 'user';
    return new;
  end if;

  new.category_final := case
    when v_text ~ '(bug|error|fall[ao]|crash|bloquead|no funciona|broken|glitch|problema)' then 'bug'
    when v_text ~ '(accesib|accessib|subt[ií]tul|colorblind|daltoni|lector de pantalla|screen reader|teclado|keyboard|contraste)' then 'accessibility'
    when v_text ~ '(lag|lento|slow|fps|rendimiento|performance|carga|loading|latencia)' then 'performance'
    when v_text ~ '(seguridad|security|privacidad|privacy|acoso|abuse|hack|estafa|scam)' then 'safety'
    when v_text ~ '(contenido|content|v[ií]deo|video|directo|stream|mapa|skin|personaje)' then 'content'
    else 'idea'
  end;
  new.classification_method := 'rules_v1';
  return new;
end;
$$;

revoke all on function fanrank_private.classify_submission() from public, anon, authenticated;
drop trigger if exists fr_submissions_classify on public.fr_submissions;
create trigger fr_submissions_classify
  before insert or update of title, details, category_requested
  on public.fr_submissions
  for each row execute function fanrank_private.classify_submission();

-- Existing rows receive an honest initial category without pretending a model classified them.
update public.fr_submissions
set category_requested = 'auto'
where category_final = 'pending';

grant insert (category_requested, ai_training_consent)
  on public.fr_submissions to anon, authenticated;
grant select (category_requested, category_final, classification_method, ai_training_consent, attachment_count)
  on public.fr_submissions to authenticated;

create table public.fr_submission_attachments (
  id uuid primary key default extensions.gen_random_uuid(),
  submission_id bigint not null references public.fr_submissions(id) on delete cascade,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  bucket_id text not null default 'fanrank-feedback-private'
    check (bucket_id = 'fanrank-feedback-private'),
  object_path text not null unique check (char_length(object_path) between 1 and 500),
  original_name text not null check (char_length(original_name) between 1 and 220),
  declared_mime text not null default '' check (char_length(declared_mime) <= 100),
  detected_mime text not null check (detected_mime in (
    'image/png','image/jpeg','image/webp'
  )),
  media_kind text not null default 'image' check (media_kind = 'image'),
  bytes bigint not null check (bytes between 1 and 5242880),
  sha256 text not null check (sha256 ~ '^[a-f0-9]{64}$'),
  safety_status text not null default 'pending'
    check (safety_status in ('pending','safe','manual_review','unsafe')),
  review_status text not null default 'quarantined'
    check (review_status in ('quarantined','approved','rejected','duplicate')),
  duplicate_of uuid references public.fr_submission_attachments(id) on delete set null,
  created_at timestamptz not null default current_timestamp
);

create index fr_submission_attachments_submission_idx
  on public.fr_submission_attachments (submission_id);
create index fr_submission_attachments_owner_idx
  on public.fr_submission_attachments (owner_user_id, created_at desc);
create index fr_submission_attachments_hash_idx
  on public.fr_submission_attachments (sha256, bytes);

alter table public.fr_submission_attachments enable row level security;
create policy fr_submission_attachments_owner_read
  on public.fr_submission_attachments
  for select to authenticated
  using (owner_user_id = (select auth.uid()));

revoke all on public.fr_submission_attachments from anon, authenticated;
grant select (id, submission_id, original_name, detected_mime, media_kind, bytes,
  safety_status, review_status, created_at)
  on public.fr_submission_attachments to authenticated;

create table fanrank_private.fr_media_intake_events (
  id bigint generated always as identity primary key,
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  bytes bigint not null check (bytes between 1 and 17825792),
  created_at timestamptz not null default current_timestamp
);

create index fr_media_intake_events_owner_idx
  on fanrank_private.fr_media_intake_events (owner_user_id, created_at desc);

create or replace function public.fr_register_media_intake(p_user_id uuid, p_bytes bigint)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_recent_10m integer;
  v_recent_day integer;
  v_bytes_day bigint;
  v_global_10m integer;
  v_global_day integer;
  v_global_bytes_day bigint;
begin
  if p_user_id is null or p_bytes is null or p_bytes < 1 or p_bytes > 17825792 then
    return false;
  end if;
  if not exists (select 1 from auth.users u where u.id = p_user_id) then
    return false;
  end if;

  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('fanrank-media-global', 0));
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(p_user_id::text, 0));
  delete from fanrank_private.fr_media_intake_events
  where created_at < current_timestamp - interval '2 days';

  select count(*) filter (where created_at >= current_timestamp - interval '10 minutes'),
         count(*) filter (where created_at >= current_timestamp - interval '1 day'),
         coalesce(sum(bytes) filter (where created_at >= current_timestamp - interval '1 day'), 0)
    into v_recent_10m, v_recent_day, v_bytes_day
  from fanrank_private.fr_media_intake_events
  where owner_user_id = p_user_id;

  select count(*) filter (where created_at >= current_timestamp - interval '10 minutes'),
         count(*) filter (where created_at >= current_timestamp - interval '1 day'),
         coalesce(sum(bytes) filter (where created_at >= current_timestamp - interval '1 day'), 0)
    into v_global_10m, v_global_day, v_global_bytes_day
  from fanrank_private.fr_media_intake_events;

  if v_recent_10m >= 3 or v_recent_day >= 10 or v_bytes_day + p_bytes > 52428800
     or v_global_10m >= 60 or v_global_day >= 500
     or v_global_bytes_day + p_bytes > 2147483648 then
    return false;
  end if;

  insert into fanrank_private.fr_media_intake_events (owner_user_id, bytes)
  values (p_user_id, p_bytes);
  return true;
end;
$$;

revoke all on function public.fr_register_media_intake(uuid, bigint)
  from public, anon, authenticated;
grant execute on function public.fr_register_media_intake(uuid, bigint) to service_role;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'fanrank-feedback-private',
  'fanrank-feedback-private',
  false,
  5242880,
  array['image/png','image/jpeg','image/webp']
)
on conflict (id) do update set
  public = false,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- No storage.objects policy is created: browsers cannot bypass the intake function.

create table public.fr_fan_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  handle text not null unique
    check (handle ~ '^[a-z0-9][a-z0-9-]{2,29}$'),
  display_name text not null check (char_length(display_name) between 2 and 50),
  headline text not null default '' check (char_length(headline) <= 160),
  skills text[] not null default '{}'
    check (
      cardinality(skills) <= 5
      and skills <@ array['tester','ux','product','accessibility','gaming','creator','engineering','other']::text[]
    ),
  is_public boolean not null default false,
  available_for_opportunities boolean not null default false,
  created_at timestamptz not null default current_timestamp,
  updated_at timestamptz not null default current_timestamp
);

create index fr_fan_profiles_public_idx
  on public.fr_fan_profiles (is_public, available_for_opportunities, created_at desc);
alter table public.fr_fan_profiles enable row level security;
create policy fr_fan_profiles_self_read
  on public.fr_fan_profiles for select to authenticated
  using (user_id = (select auth.uid()));
create policy fr_fan_profiles_self_insert
  on public.fr_fan_profiles for insert to authenticated
  with check (user_id = (select auth.uid()));
create policy fr_fan_profiles_self_update
  on public.fr_fan_profiles for update to authenticated
  using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));

revoke all on public.fr_fan_profiles from anon, authenticated;
grant select on public.fr_fan_profiles to authenticated;
grant insert (user_id, handle, display_name, headline, skills, is_public, available_for_opportunities)
  on public.fr_fan_profiles to authenticated;
grant update (handle, display_name, headline, skills, is_public, available_for_opportunities)
  on public.fr_fan_profiles to authenticated;

create or replace function fanrank_private.touch_fan_profile_updated_at()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  new.updated_at := current_timestamp;
  return new;
end;
$$;

revoke all on function fanrank_private.touch_fan_profile_updated_at()
  from public, anon, authenticated;
create trigger fr_fan_profiles_touch_updated_at
  before update on public.fr_fan_profiles
  for each row execute function fanrank_private.touch_fan_profile_updated_at();

create or replace function fanrank_private.fan_impact(p_user_id uuid)
returns table(
  impact_points integer,
  published_ideas integer,
  team_hearts integer,
  fan_votes integer,
  top_suggestions jsonb
)
language sql
stable
security definer
set search_path = ''
as $$
  with contributions as (
    select distinct on (s.canonical_idea_id)
      s.canonical_idea_id,
      s.section,
      i.title,
      i.title_es,
      i.web_votes,
      i.team_interest_count
    from public.fr_submissions s
    join public.fr_ideas i on i.id = s.canonical_idea_id and i.approved = true
    where s.user_id = p_user_id
      and s.attribution_mode = 'account'
      and s.status in ('published','merged')
      and s.canonical_idea_id is not null
    order by s.canonical_idea_id, s.created_at
  ), scored as (
    select c.*,
      2
      + least(4::numeric, pg_catalog.ln(1 + c.web_votes) / pg_catalog.ln(2::numeric))
      + case when c.team_interest_count > 0 then 4 else 0 end as contribution_score
    from contributions c
  ), ranked as (
    select section, title, title_es, canonical_idea_id, web_votes, team_interest_count,
           contribution_score
    from scored
    order by contribution_score desc, team_interest_count desc, web_votes desc, canonical_idea_id
    limit 5
  ), totals as (
    select count(*)::integer as published_ideas,
           count(*) filter (where team_interest_count > 0)::integer as team_hearts,
           coalesce(sum(web_votes), 0)::integer as fan_votes
    from scored
  ), score_total as (
    select coalesce(sum(contribution_score), 0) as points
    from ranked
  )
  select least(100, pg_catalog.round(2 * s.points))::integer,
    t.published_ideas,
    t.team_hearts,
    t.fan_votes,
    coalesce((
      select jsonb_agg(jsonb_build_object(
        'section', r.section,
        'title', r.title,
        'title_es', r.title_es,
        'idea_id', r.canonical_idea_id,
        'fan_votes', r.web_votes,
        'team_hearts', r.team_interest_count
      ) order by r.contribution_score desc, r.team_interest_count desc, r.web_votes desc, r.canonical_idea_id)
      from ranked r
    ), '[]'::jsonb)
  from totals t
  cross join score_total s;
$$;

revoke all on function fanrank_private.fan_impact(uuid)
  from public, anon, authenticated;

create or replace function public.fr_my_fan_profile()
returns table(
  handle text,
  display_name text,
  headline text,
  skills text[],
  is_public boolean,
  available_for_opportunities boolean,
  impact_points integer,
  published_ideas integer,
  team_hearts integer,
  fan_votes integer,
  top_suggestions jsonb
)
language sql
stable
security definer
set search_path = ''
as $$
  select p.handle, p.display_name, p.headline, p.skills, p.is_public,
         p.available_for_opportunities, i.impact_points, i.published_ideas,
         i.team_hearts, i.fan_votes, i.top_suggestions
  from public.fr_fan_profiles p
  cross join lateral fanrank_private.fan_impact(p.user_id) i
  where p.user_id = auth.uid();
$$;

create or replace function public.fr_public_fan_profile(p_handle text)
returns table(
  handle text,
  display_name text,
  headline text,
  skills text[],
  available_for_opportunities boolean,
  impact_points integer,
  published_ideas integer,
  team_hearts integer,
  fan_votes integer,
  top_suggestions jsonb
)
language sql
stable
security definer
set search_path = ''
as $$
  select p.handle, p.display_name, p.headline, p.skills,
         p.available_for_opportunities, i.impact_points, i.published_ideas,
         i.team_hearts, i.fan_votes, i.top_suggestions
  from public.fr_fan_profiles p
  cross join lateral fanrank_private.fan_impact(p.user_id) i
  where p.handle = pg_catalog.lower(pg_catalog.btrim(p_handle))
    and p.is_public = true
  limit 1;
$$;

create or replace function public.fr_upsert_my_fan_profile(
  p_handle text,
  p_display_name text,
  p_headline text default '',
  p_skills text[] default '{}',
  p_is_public boolean default false,
  p_available_for_opportunities boolean default false
)
returns table(
  handle text,
  display_name text,
  headline text,
  skills text[],
  is_public boolean,
  available_for_opportunities boolean
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_actor uuid := auth.uid();
  v_handle text := pg_catalog.lower(pg_catalog.btrim(p_handle));
  v_display_name text := pg_catalog.btrim(p_display_name);
  v_headline text := pg_catalog.btrim(coalesce(p_headline, ''));
  v_skills text[] := coalesce(p_skills, '{}');
begin
  if v_actor is null then
    raise exception using errcode = '42501', message = 'Authenticated fan required';
  end if;
  if v_handle !~ '^[a-z0-9][a-z0-9-]{2,29}$'
     or char_length(v_display_name) not between 2 and 50
     or char_length(v_headline) > 160
     or cardinality(v_skills) > 5
     or not (v_skills <@ array['tester','ux','product','accessibility','gaming','creator','engineering','other']::text[]) then
    raise exception using errcode = '22023', message = 'Invalid fan profile';
  end if;

  insert into public.fr_fan_profiles (
    user_id, handle, display_name, headline, skills, is_public, available_for_opportunities
  ) values (
    v_actor, v_handle, v_display_name, v_headline, v_skills,
    coalesce(p_is_public, false),
    coalesce(p_available_for_opportunities, false)
  )
  on conflict (user_id) do update set
    handle = excluded.handle,
    display_name = excluded.display_name,
    headline = excluded.headline,
    skills = excluded.skills,
    is_public = excluded.is_public,
    available_for_opportunities = excluded.available_for_opportunities;

  return query
  select p.handle, p.display_name, p.headline, p.skills, p.is_public,
         p.available_for_opportunities
  from public.fr_fan_profiles p
  where p.user_id = v_actor;
end;
$$;

create or replace function public.fr_set_submission_ai_consent(
  p_submission_id bigint,
  p_consent boolean
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
begin
  if auth.uid() is null or p_submission_id is null or p_consent is null then
    raise exception using errcode = '42501', message = 'Authenticated owner required';
  end if;
  update public.fr_submissions
  set ai_training_consent = p_consent
  where id = p_submission_id and user_id = auth.uid();
  return found;
end;
$$;

revoke all on function public.fr_my_fan_profile() from public, anon, authenticated;
grant execute on function public.fr_my_fan_profile() to authenticated;
revoke all on function public.fr_public_fan_profile(text) from public, anon, authenticated;
grant execute on function public.fr_public_fan_profile(text) to anon, authenticated;
revoke all on function public.fr_upsert_my_fan_profile(text, text, text, text[], boolean, boolean)
  from public, anon, authenticated;
grant execute on function public.fr_upsert_my_fan_profile(text, text, text, text[], boolean, boolean)
  to authenticated;
revoke all on function public.fr_set_submission_ai_consent(bigint, boolean)
  from public, anon, authenticated;
grant execute on function public.fr_set_submission_ai_consent(bigint, boolean)
  to authenticated;

alter table public.fr_events
  drop constraint if exists fr_events_event_check;
alter table public.fr_events
  add constraint fr_events_event_check
  check (event in (
    'page_view', 'search', 'profile_open', 'idea_open', 'idea_share', 'vote', 'submission',
    'section_request', 'claim_request', 'suggest_open', 'similar_vote', 'auth_open',
    'auth_link_requested', 'auth_recovery_requested', 'auth_signed_in', 'auth_signed_out',
    'activity_open', 'team_interest', 'team_invite_created', 'owner_mode_open', 'owner_feedback',
    'owner_profile_request', 'profile_image_updated', 'promotion_interest', 'pro_interest',
    'media_added', 'fan_profile_saved', 'fan_profile_open'
  ));

comment on table public.fr_submission_attachments is
  'Private quarantine metadata. Files are never public and only the server-side intake may write them.';
comment on column public.fr_submissions.ai_training_consent is
  'Separate, optional and revocable permission. False by default and never implied by submission.';
comment on function fanrank_private.fan_impact(uuid) is
  '0-100 score from the five best public-attributed canonical ideas; votes are logarithmic and team interest is binary per idea.';

commit;

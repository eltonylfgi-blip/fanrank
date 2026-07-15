-- FanRank v9: official team stars are an auditable signal separate from organic rank.

begin;

alter table public.fr_sections
  add column team_member_star_cap smallint not null default 1;
alter table public.fr_sections
  add constraint fr_sections_team_member_star_cap_check
  check (team_member_star_cap in (1, 3));

alter table public.fr_team_interests
  add column star_value smallint not null default 1;
alter table public.fr_team_interests
  add constraint fr_team_interests_star_value_check
  check (star_value between 1 and 5);

alter table public.fr_ideas
  add column owner_star_value smallint not null default 0,
  add column team_star_support_count integer not null default 0;
alter table public.fr_ideas
  add constraint fr_ideas_owner_star_value_check
    check (owner_star_value between 0 and 5),
  add constraint fr_ideas_team_star_support_count_check
    check (team_star_support_count >= 0);

create or replace function fanrank_private.sync_team_interest_count()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_idea_id integer;
  v_count integer;
  v_owner_star smallint;
  v_team_support integer;
begin
  if tg_op = 'DELETE' then
    v_idea_id := old.idea_id;
  else
    v_idea_id := new.idea_id;
  end if;

  select
    count(*)::integer,
    coalesce(max(ti.star_value) filter (where pm.role = 'owner'), 0)::smallint,
    count(*) filter (where pm.role <> 'owner')::integer
  into v_count, v_owner_star, v_team_support
  from public.fr_team_interests ti
  join public.fr_profile_members pm
    on pm.section = ti.section and pm.user_id = ti.selected_by
  where ti.idea_id = v_idea_id
    and ti.revoked_at is null
    and pm.status = 'active';

  update public.fr_ideas
  set team_interest_count = coalesce(v_count, 0),
      owner_pick = coalesce(v_owner_star, 0) > 0,
      owner_star_value = coalesce(v_owner_star, 0),
      team_star_support_count = coalesce(v_team_support, 0)
  where id = v_idea_id;

  if tg_op = 'DELETE' then return old; end if;
  return new;
end;
$$;
revoke all on function fanrank_private.sync_team_interest_count() from public;

drop trigger if exists fr_team_interests_sync_count on public.fr_team_interests;
create trigger fr_team_interests_sync_count
  after insert or update of revoked_at, star_value or delete
  on public.fr_team_interests
  for each row execute function fanrank_private.sync_team_interest_count();

create or replace function fanrank_private.sync_member_team_counts()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  update public.fr_ideas i
  set team_interest_count = (
        select count(*)::integer
        from public.fr_team_interests ti
        join public.fr_profile_members pm
          on pm.section = ti.section and pm.user_id = ti.selected_by
        where ti.idea_id = i.id and ti.revoked_at is null and pm.status = 'active'
      ),
      owner_star_value = coalesce((
        select max(ti.star_value)::smallint
        from public.fr_team_interests ti
        join public.fr_profile_members pm
          on pm.section = ti.section and pm.user_id = ti.selected_by
        where ti.idea_id = i.id and ti.revoked_at is null and pm.status = 'active' and pm.role = 'owner'
      ), 0),
      team_star_support_count = (
        select count(*)::integer
        from public.fr_team_interests ti
        join public.fr_profile_members pm
          on pm.section = ti.section and pm.user_id = ti.selected_by
        where ti.idea_id = i.id and ti.revoked_at is null and pm.status = 'active' and pm.role <> 'owner'
      ),
      owner_pick = exists (
        select 1
        from public.fr_team_interests ti
        join public.fr_profile_members pm
          on pm.section = ti.section and pm.user_id = ti.selected_by
        where ti.idea_id = i.id and ti.revoked_at is null and pm.status = 'active' and pm.role = 'owner'
      )
  where i.section = new.section;
  return new;
end;
$$;
revoke all on function fanrank_private.sync_member_team_counts() from public;

update public.fr_ideas i
set team_interest_count = (
      select count(*)::integer
      from public.fr_team_interests ti
      join public.fr_profile_members pm
        on pm.section = ti.section and pm.user_id = ti.selected_by
      where ti.idea_id = i.id and ti.revoked_at is null and pm.status = 'active'
    ),
    owner_star_value = coalesce((
      select max(ti.star_value)::smallint
      from public.fr_team_interests ti
      join public.fr_profile_members pm
        on pm.section = ti.section and pm.user_id = ti.selected_by
      where ti.idea_id = i.id and ti.revoked_at is null and pm.status = 'active' and pm.role = 'owner'
    ), 0),
    team_star_support_count = (
      select count(*)::integer
      from public.fr_team_interests ti
      join public.fr_profile_members pm
        on pm.section = ti.section and pm.user_id = ti.selected_by
      where ti.idea_id = i.id and ti.revoked_at is null and pm.status = 'active' and pm.role <> 'owner'
    ),
    owner_pick = exists (
      select 1
      from public.fr_team_interests ti
      join public.fr_profile_members pm
        on pm.section = ti.section and pm.user_id = ti.selected_by
      where ti.idea_id = i.id and ti.revoked_at is null and pm.status = 'active' and pm.role = 'owner'
    );

create or replace function public.fr_set_team_star(p_idea_id integer, p_value integer)
returns table(
  owner_star_value smallint,
  team_star_support_count integer,
  team_interest_count integer,
  my_star_value smallint
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_actor uuid := auth.uid();
  v_section text;
  v_role text;
  v_cap smallint;
begin
  if v_actor is null then
    raise exception using errcode = '42501', message = 'Authenticated member required';
  end if;
  if p_value is null or p_value < 0 or p_value > 5 then
    raise exception using errcode = '22023', message = 'Star value must be between 0 and 5';
  end if;

  select i.section into v_section
  from public.fr_ideas i
  where i.id = p_idea_id and i.approved;
  if v_section is null then
    raise exception using errcode = '22023', message = 'Published idea required';
  end if;

  select pm.role, s.team_member_star_cap into v_role, v_cap
  from public.fr_profile_members pm
  join public.fr_sections s on s.slug = pm.section
  where pm.section = v_section
    and pm.user_id = v_actor
    and pm.status = 'active'
    and s.verification_status = 'verified';
  if v_role is null then
    raise exception using errcode = '42501', message = 'Verified team membership required';
  end if;
  if p_value > (case when v_role = 'owner' then 5 else v_cap end) then
    raise exception using errcode = '42501', message = 'Star value exceeds this membership limit';
  end if;

  if p_value = 0 then
    update public.fr_team_interests
    set revoked_at = current_timestamp, revoked_by = v_actor
    where idea_id = p_idea_id and selected_by = v_actor and revoked_at is null;
  else
    insert into public.fr_team_interests (idea_id, section, selected_by, star_value)
    values (p_idea_id, v_section, v_actor, p_value::smallint)
    on conflict (idea_id, selected_by) where revoked_at is null
    do update set star_value = excluded.star_value, selected_at = current_timestamp;
  end if;

  return query
  select i.owner_star_value, i.team_star_support_count, i.team_interest_count, p_value::smallint
  from public.fr_ideas i
  where i.id = p_idea_id;
end;
$$;

create or replace function public.fr_my_team_stars(p_section text)
returns table(idea_id integer, star_value smallint)
language sql
security definer
set search_path = ''
as $$
  select ti.idea_id, ti.star_value
  from public.fr_team_interests ti
  join public.fr_profile_members pm
    on pm.section = ti.section and pm.user_id = ti.selected_by
  join public.fr_sections s on s.slug = pm.section
  where ti.section = p_section
    and ti.selected_by = auth.uid()
    and ti.revoked_at is null
    and pm.status = 'active'
    and s.verification_status = 'verified';
$$;

create or replace function public.fr_set_team_star_cap(p_section text, p_cap integer)
returns table(team_member_star_cap smallint)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_actor uuid := auth.uid();
begin
  if v_actor is null or p_cap not in (1, 3) then
    raise exception using errcode = '42501', message = 'Verified owner and a cap of 1 or 3 required';
  end if;
  if not exists (
    select 1
    from public.fr_profile_members pm
    join public.fr_sections s on s.slug = pm.section
    where pm.section = p_section
      and pm.user_id = v_actor
      and pm.role = 'owner'
      and pm.status = 'active'
      and s.verification_status = 'verified'
  ) then
    raise exception using errcode = '42501', message = 'Verified owner required';
  end if;

  update public.fr_sections
  set team_member_star_cap = p_cap::smallint
  where slug = p_section;

  update public.fr_team_interests ti
  set star_value = least(ti.star_value, p_cap::smallint)
  from public.fr_profile_members pm
  where ti.section = p_section
    and ti.section = pm.section
    and ti.selected_by = pm.user_id
    and pm.role <> 'owner'
    and pm.status = 'active'
    and ti.revoked_at is null
    and ti.star_value > p_cap;

  return query select p_cap::smallint;
end;
$$;

revoke all on function public.fr_set_team_star(integer, integer) from public, anon, authenticated;
revoke all on function public.fr_my_team_stars(text) from public, anon, authenticated;
revoke all on function public.fr_set_team_star_cap(text, integer) from public, anon, authenticated;
grant execute on function public.fr_set_team_star(integer, integer) to authenticated;
grant execute on function public.fr_my_team_stars(text) to authenticated;
grant execute on function public.fr_set_team_star_cap(text, integer) to authenticated;

create or replace view public.fr_ranking
with (security_invoker = true)
as
select
  i.id,
  i.section,
  i.title,
  i.title_es,
  i.source_url,
  i.origin_upvotes,
  i.ai_score,
  i.ai_reason,
  i.ai_reason_es,
  i.owner_pick,
  i.web_votes,
  i.team_interest_count,
  i.owner_star_value,
  i.team_star_support_count
from public.fr_ideas i
where i.approved = true;

create or replace view public.fr_sections_stats
with (security_invoker = true)
as
select
  s.slug,
  s.name,
  s.emoji,
  s.kind,
  s.tagline,
  s.tagline_es,
  count(i.id)::integer as ideas,
  coalesce(sum(i.origin_upvotes), 0)::integer as reddit_upvotes,
  coalesce(sum(i.web_votes), 0)::integer as fan_votes,
  s.verification_status,
  s.tags,
  s.featured_rank,
  count(i.id) filter (where i.created_at >= now() - interval '30 days')::integer as recent_ideas,
  s.image_path,
  s.image_alt,
  s.image_source_url,
  s.image_credit,
  s.image_rights,
  s.team_member_star_cap
from public.fr_sections s
left join public.fr_ideas i
  on i.section = s.slug and i.approved = true
group by s.slug;
grant select on public.fr_ranking, public.fr_sections_stats to anon, authenticated;

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
    'promotion_interest', 'pro_interest'
  ));

comment on column public.fr_ideas.owner_star_value is
  'Official owner rating from 0 to 5; displayed separately and excluded from organic rank.';
comment on column public.fr_ideas.team_star_support_count is
  'Number of active non-owner team members rating the idea; never summed into organic rank.';
comment on function public.fr_set_team_star(integer, integer) is
  'Idempotent verified-team rating. Owner max 5; other roles obey the owner-selected cap.';

commit;

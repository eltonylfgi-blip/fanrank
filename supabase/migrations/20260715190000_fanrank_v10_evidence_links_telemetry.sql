-- FanRank v10: anonymous-safe supporting links and trustworthy product telemetry.
-- Links are stored privately with the submission and are never fetched by Postgres.

begin;

create or replace function public.fr_valid_evidence_links(p_links text[])
returns boolean
language plpgsql
immutable
set search_path = ''
as $$
declare
  item text;
  seen text[] := '{}'::text[];
begin
  if p_links is null or cardinality(p_links) > 3 or array_position(p_links, null) is not null then
    return false;
  end if;

  foreach item in array p_links loop
    if item <> btrim(item)
      or char_length(item) < 9
      or char_length(item) > 2048
      or item !~ '^https://[^/@[:space:]]+([/?]|$)'
      or item ~ '^https://[^/]*@'
      or position('#' in item) > 0
      or item = any(seen)
    then
      return false;
    end if;
    seen := array_append(seen, item);
  end loop;

  return true;
end;
$$;

revoke all on function public.fr_valid_evidence_links(text[])
  from public, anon, authenticated;
grant execute on function public.fr_valid_evidence_links(text[]) to anon, authenticated, service_role;

alter table public.fr_submissions
  add column evidence_links text[] not null default '{}'::text[];

alter table public.fr_submissions
  add constraint fr_submissions_evidence_links_check
    check (public.fr_valid_evidence_links(evidence_links)),
  add constraint fr_submissions_total_evidence_check
    check (attachment_count + cardinality(evidence_links) <= 3);

grant insert (evidence_links) on public.fr_submissions to anon, authenticated;
grant select (evidence_links) on public.fr_submissions to authenticated;

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
    'promotion_interest', 'pro_interest', 'media_added', 'fan_profile_saved', 'fan_profile_open'
  ));

comment on column public.fr_submissions.evidence_links is
  'Up to three private HTTPS supporting links. The server never fetches them; approved public source links require separate moderation.';

commit;

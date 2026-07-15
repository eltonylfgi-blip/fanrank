-- FanRank v11: canonical YouTube evidence and a least-privilege team inbox.
-- This migration does not make submissions or evidence public.

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
    if item <> pg_catalog.btrim(item)
      or pg_catalog.char_length(item) < 9
      or pg_catalog.char_length(item) > 2048
      or item !~ '^https://[^/@[:space:]]+([/?]|$)'
      or item ~ '^https://[^/]*@'
      or pg_catalog.strpos(item, '#') > 0
      or item = any(seen)
    then
      return false;
    end if;

    -- Any URL that looks like YouTube must already be the canonical URL
    -- produced by the trusted parsers. Generic HTTPS links remain valid.
    if (
      position('youtube' in pg_catalog.lower(item)) > 0
      or position('youtu.be' in pg_catalog.lower(item)) > 0
    ) and item !~ '^https://www[.]youtube[.]com/watch[?]v=[A-Za-z0-9_-]{11}$'
    then
      return false;
    end if;

    seen := pg_catalog.array_append(seen, item);
  end loop;

  return true;
end;
$$;

revoke all on function public.fr_valid_evidence_links(text[])
  from public, anon, authenticated;
grant execute on function public.fr_valid_evidence_links(text[])
  to anon, authenticated, service_role;

-- Recreate the CHECK so existing rows are evaluated against the stricter
-- function too. If any historical value is unsafe, the transaction aborts
-- without silently rewriting user evidence.
alter table public.fr_submissions
  drop constraint fr_submissions_evidence_links_check;
alter table public.fr_submissions
  add constraint fr_submissions_evidence_links_check
  check (public.fr_valid_evidence_links(evidence_links));

create or replace function public.fr_team_submission_inbox(
  p_section text,
  p_limit integer default 50
)
returns table (
  id bigint,
  section text,
  title text,
  details text,
  author text,
  contact text,
  language text,
  status text,
  canonical_idea_id integer,
  category_requested text,
  category_final text,
  classification_method text,
  attachment_count smallint,
  evidence_links text[],
  can_contact boolean,
  created_at timestamptz
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_actor uuid := auth.uid();
  v_section text := pg_catalog.btrim(p_section);
  v_limit integer := least(greatest(coalesce(p_limit, 50), 1), 50);
  v_authorized boolean;
begin
  if v_actor is null then
    raise exception using errcode = '42501', message = 'Authenticated team member required';
  end if;

  if v_section is null or pg_catalog.char_length(v_section) not between 1 and 120 then
    raise exception using errcode = '22023', message = 'Valid profile section required';
  end if;

  select
    exists (
      select 1
      from public.fr_platform_admins as a
      where a.user_id = v_actor
        and a.status = 'active'
    )
    or exists (
      select 1
      from public.fr_profile_members as m
      join public.fr_sections as s on s.slug = m.section
      where m.user_id = v_actor
        and m.section = v_section
        and m.role in ('owner', 'admin')
        and m.status = 'active'
        and s.verification_status = 'verified'
    )
  into v_authorized;

  if not coalesce(v_authorized, false) then
    raise exception using errcode = '42501', message = 'Verified profile owner or administrator required';
  end if;

  return query
  select
    submission.id,
    submission.section,
    submission.title,
    submission.details,
    case when submission.allow_contact then submission.author else null end as author,
    case when submission.allow_contact then submission.contact else null end as contact,
    submission.language,
    submission.status,
    submission.canonical_idea_id,
    submission.category_requested,
    submission.category_final,
    submission.classification_method,
    submission.attachment_count,
    submission.evidence_links,
    submission.allow_contact as can_contact,
    submission.created_at
  from public.fr_submissions as submission
  where submission.section = v_section
    and submission.status = 'received'
  order by submission.created_at desc, submission.id desc
  limit v_limit;
end;
$$;

revoke all on function public.fr_team_submission_inbox(text, integer)
  from public, anon, authenticated;
grant execute on function public.fr_team_submission_inbox(text, integer)
  to authenticated;

comment on function public.fr_team_submission_inbox(text, integer) is
  'Private submission inbox for active platform admins or active owner/admin members of the matching verified profile. Author and contact are returned only with explicit contact consent.';

commit;

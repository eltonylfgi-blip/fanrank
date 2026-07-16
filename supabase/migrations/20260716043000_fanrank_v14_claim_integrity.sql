-- FanRank v14: a verified profile cannot receive a new claim and one user cannot spam duplicate pending claims.

begin;

create unique index if not exists fr_claims_one_pending_per_user_section_idx
  on public.fr_claims(section, user_id)
  where status = 'pending';

create or replace function fanrank_private.fr_validate_pending_claim_target()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.status = 'pending' and not exists (
    select 1
    from public.fr_sections as section_row
    where section_row.slug = new.section
      and section_row.verification_status is distinct from 'verified'
  ) then
    raise exception using errcode = '23514', message = 'Verified profiles cannot receive new claims';
  end if;
  return new;
end;
$$;

revoke all on function fanrank_private.fr_validate_pending_claim_target()
  from public, anon, authenticated;

drop trigger if exists fr_claims_validate_pending_target on public.fr_claims;
create trigger fr_claims_validate_pending_target
  before insert or update of section, user_id, status on public.fr_claims
  for each row execute function fanrank_private.fr_validate_pending_claim_target();

drop policy if exists fr_claims_authenticated_insert on public.fr_claims;
create policy fr_claims_authenticated_insert on public.fr_claims
  for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and status = 'pending'
    and exists (
      select 1
      from public.fr_sections as section_row
      where section_row.slug = fr_claims.section
        and section_row.verification_status is distinct from 'verified'
    )
  );

comment on function fanrank_private.fr_validate_pending_claim_target() is
  'Rejects new pending claims once a profile is verified. Duplicate pending claims are blocked by a partial unique index.';

commit;

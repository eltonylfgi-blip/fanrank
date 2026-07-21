begin;

-- FanRank v22: verified profile owners/admins can send private, contextual feedback
-- with screenshots. A local MADRE drain reads only `new` rows with the service key
-- and writes the review receipt into BUZON_ENTRANTE; neither the feedback nor its
-- storage object is ever public. Screenshot writes themselves go through the
-- JWT-protected Edge Function because storage.objects is provider-owned and
-- its policies cannot be safely altered from this migration role.

alter table public.fr_owner_feedback
  add column if not exists section text references public.fr_sections(slug) on delete set null;

create index if not exists fr_owner_feedback_new_created_idx
  on public.fr_owner_feedback (created_at asc)
  where status = 'new';

create index if not exists fr_owner_feedback_section_created_idx
  on public.fr_owner_feedback (section, created_at desc)
  where section is not null;

grant select (section) on public.fr_owner_feedback to authenticated;
grant insert (section) on public.fr_owner_feedback to authenticated;

drop policy if exists fr_owner_feedback_creator_read_own on public.fr_owner_feedback;
create policy fr_owner_feedback_creator_read_own
on public.fr_owner_feedback
for select
to authenticated
using (
  user_id = (select auth.uid())
  and exists (
    select 1
    from public.fr_profile_members as member
    join public.fr_sections as profile on profile.slug = member.section
    where member.user_id = (select auth.uid())
      and member.section = fr_owner_feedback.section
      and member.status = 'active'
      and member.role in ('owner', 'admin')
      and profile.verification_status = 'verified'
  )
);

drop policy if exists fr_owner_feedback_creator_insert on public.fr_owner_feedback;
create policy fr_owner_feedback_creator_insert
on public.fr_owner_feedback
for insert
to authenticated
with check (
  user_id = (select auth.uid())
  and section is not null
  and exists (
    select 1
    from public.fr_profile_members as member
    join public.fr_sections as profile on profile.slug = member.section
    where member.user_id = (select auth.uid())
      and member.section = fr_owner_feedback.section
      and member.status = 'active'
      and member.role in ('owner', 'admin')
      and profile.verification_status = 'verified'
  )
);

comment on column public.fr_owner_feedback.section is
  'Verified profile the feedback belongs to. NULL remains valid only for platform-admin feedback about FanRank itself. Screenshot writes use the JWT-protected Edge Function.';
comment on policy fr_owner_feedback_creator_insert on public.fr_owner_feedback is
  'Only an active owner/admin of the same verified profile may submit contextual creator feedback.';

commit;

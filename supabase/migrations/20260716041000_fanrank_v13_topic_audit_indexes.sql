-- FanRank v13: keep Auth user deletion and topic audit lookups scalable.

begin;

create index fr_profile_topics_created_by_idx
  on public.fr_profile_topics(created_by)
  where created_by is not null;

create index fr_profile_topics_updated_by_idx
  on public.fr_profile_topics(updated_by)
  where updated_by is not null;

commit;

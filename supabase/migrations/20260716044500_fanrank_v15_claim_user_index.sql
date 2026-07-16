-- FanRank v15: cover the Auth user foreign key for claim lookup and deletion.

begin;

create index if not exists fr_claims_user_id_idx
  on public.fr_claims(user_id);

commit;

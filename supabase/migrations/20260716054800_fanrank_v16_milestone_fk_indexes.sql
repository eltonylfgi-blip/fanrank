-- FanRank v16 follow-up: cover private milestone foreign keys for queued lookups.

create index if not exists fr_milestone_subscriptions_user_idx
  on fanrank_private.fr_milestone_subscriptions(user_id)
  where user_id is not null;

create index if not exists fr_milestone_outbox_idea_idx
  on fanrank_private.fr_milestone_outbox(idea_id);

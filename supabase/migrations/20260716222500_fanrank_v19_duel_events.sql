-- FanRank v19: permite los eventos del Duelo de ideas en la telemetría (aditivo).
-- Aplicada en producción el 2026-07-16 ~22:25 via Supabase MCP (apply_migration).
alter table public.fr_events
  drop constraint if exists fr_events_event_check;

alter table public.fr_events
  add constraint fr_events_event_check
  check (event in (
    'page_view','search','profile_open','idea_open','idea_share','vote','submission',
    'section_request','claim_request','suggest_open','similar_vote','auth_open',
    'auth_link_requested','auth_recovery_requested','auth_signed_in','auth_signed_out',
    'activity_open','team_interest','team_star','team_star_cap','team_invite_created',
    'owner_mode_open','owner_feedback','owner_profile_request','profile_image_updated',
    'promotion_interest','pro_interest','media_added','fan_profile_saved','fan_profile_open',
    'owner_cta_open','topic_filter','topic_created','topic_archived','topic_assigned',
    'alert_optin','duel_open','duel_pick'
  ));

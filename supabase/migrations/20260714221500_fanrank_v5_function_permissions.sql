-- Supabase may provision API roles with default function execution.
-- Make the intended public/authenticated boundary explicit and testable.

REVOKE ALL ON FUNCTION public.fr_submission_status(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.fr_submission_status(text) TO anon, authenticated;

REVOKE ALL ON FUNCTION public.fr_set_team_interest(integer, boolean) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.fr_my_team_interests(text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.fr_create_profile_invite(text, text, text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.fr_preview_profile_invite(text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.fr_accept_profile_invite(text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.fr_profile_team(text) FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.fr_revoke_profile_member(text, uuid) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.fr_set_team_interest(integer, boolean) TO authenticated;
GRANT EXECUTE ON FUNCTION public.fr_my_team_interests(text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.fr_create_profile_invite(text, text, text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.fr_preview_profile_invite(text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.fr_accept_profile_invite(text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.fr_profile_team(text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.fr_revoke_profile_member(text, uuid) TO authenticated;

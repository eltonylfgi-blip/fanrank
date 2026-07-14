-- FanRank v5: private voting, optional accounts, verified multi-member teams.
-- Public data is limited to approved ideas and aggregate signals.

CREATE SCHEMA IF NOT EXISTS fanrank_private;
REVOKE ALL ON SCHEMA fanrank_private FROM PUBLIC, anon, authenticated;

ALTER TABLE public.fr_sections
  ADD COLUMN verification_status text NOT NULL DEFAULT 'unverified',
  ADD COLUMN verified_at timestamptz;
ALTER TABLE public.fr_sections
  ADD CONSTRAINT fr_sections_verification_status_check
  CHECK (verification_status IN ('unverified', 'pending', 'verified'));

ALTER TABLE public.fr_ideas
  ADD COLUMN web_votes integer NOT NULL DEFAULT 0,
  ADD COLUMN team_interest_count integer NOT NULL DEFAULT 0;
ALTER TABLE public.fr_ideas
  ADD CONSTRAINT fr_ideas_web_votes_nonnegative CHECK (web_votes >= 0),
  ADD CONSTRAINT fr_ideas_team_interest_count_nonnegative CHECK (team_interest_count >= 0);
UPDATE public.fr_ideas AS i
SET web_votes = COALESCE((SELECT count(*)::integer FROM public.fr_votes AS v WHERE v.idea_id = i.id), 0),
    team_interest_count = 0,
    owner_pick = false;

ALTER TABLE public.fr_votes
  ADD COLUMN user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE;
CREATE UNIQUE INDEX fr_votes_authenticated_once
  ON public.fr_votes (idea_id, user_id)
  WHERE user_id IS NOT NULL;

DROP POLICY IF EXISTS fr_votes_public_read ON public.fr_votes;
DROP POLICY IF EXISTS fr_votes_public_insert ON public.fr_votes;
CREATE POLICY fr_votes_anon_insert ON public.fr_votes
  FOR INSERT TO anon
  WITH CHECK (
    (SELECT auth.uid()) IS NULL
    AND user_id IS NULL
    AND voter NOT LIKE 'user:%'
    AND char_length(btrim(voter)) BETWEEN 8 AND 100
    AND EXISTS (SELECT 1 FROM public.fr_ideas AS i WHERE i.id = idea_id AND i.approved)
  );
CREATE POLICY fr_votes_authenticated_insert ON public.fr_votes
  FOR INSERT TO authenticated
  WITH CHECK (
    (SELECT auth.uid()) IS NOT NULL
    AND user_id = (SELECT auth.uid())
    AND voter = 'user:' || (SELECT auth.uid())::text
    AND EXISTS (SELECT 1 FROM public.fr_ideas AS i WHERE i.id = idea_id AND i.approved)
  );
REVOKE ALL ON public.fr_votes FROM anon, authenticated;
GRANT INSERT (idea_id, voter, user_id) ON public.fr_votes TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.fr_votes_id_seq TO anon, authenticated;

CREATE OR REPLACE FUNCTION fanrank_private.sync_vote_count()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    UPDATE public.fr_ideas
    SET web_votes = web_votes + 1
    WHERE id = NEW.idea_id;
    RETURN NEW;
  END IF;

  UPDATE public.fr_ideas
  SET web_votes = GREATEST(0, web_votes - 1)
  WHERE id = OLD.idea_id;
  RETURN OLD;
END;
$$;
REVOKE ALL ON FUNCTION fanrank_private.sync_vote_count() FROM PUBLIC;
DROP TRIGGER IF EXISTS fr_votes_sync_count ON public.fr_votes;
CREATE TRIGGER fr_votes_sync_count
  AFTER INSERT OR DELETE ON public.fr_votes
  FOR EACH ROW EXECUTE FUNCTION fanrank_private.sync_vote_count();

ALTER TABLE public.fr_submissions
  ADD COLUMN user_id uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  ADD COLUMN attribution_mode text NOT NULL DEFAULT 'anonymous',
  ADD COLUMN allow_contact boolean NOT NULL DEFAULT false,
  ADD COLUMN status text NOT NULL DEFAULT 'received',
  ADD COLUMN canonical_idea_id integer REFERENCES public.fr_ideas(id) ON DELETE SET NULL,
  ADD COLUMN receipt_hash text;
ALTER TABLE public.fr_submissions
  ADD CONSTRAINT fr_submissions_attribution_mode_check
    CHECK (attribution_mode IN ('anonymous', 'account')),
  ADD CONSTRAINT fr_submissions_status_check
    CHECK (status IN ('received', 'published', 'merged', 'rejected', 'hidden')),
  ADD CONSTRAINT fr_submissions_receipt_hash_check
    CHECK (receipt_hash IS NULL OR receipt_hash ~ '^[0-9a-f]{64}$');
CREATE UNIQUE INDEX fr_submissions_receipt_hash_unique
  ON public.fr_submissions (receipt_hash)
  WHERE receipt_hash IS NOT NULL;
UPDATE public.fr_submissions
SET status = CASE WHEN approved THEN 'published' ELSE 'received' END;

DROP POLICY IF EXISTS fr_submissions_public_insert ON public.fr_submissions;
CREATE POLICY fr_submissions_anon_insert ON public.fr_submissions
  FOR INSERT TO anon
  WITH CHECK (
    (SELECT auth.uid()) IS NULL
    AND user_id IS NULL
    AND attribution_mode = 'anonymous'
    AND status = 'received'
    AND approved = false
    AND canonical_idea_id IS NULL
    AND receipt_hash ~ '^[0-9a-f]{64}$'
    AND ((contact IS NULL AND allow_contact = false) OR (contact IS NOT NULL AND allow_contact = true))
  );
CREATE POLICY fr_submissions_authenticated_insert ON public.fr_submissions
  FOR INSERT TO authenticated
  WITH CHECK (
    (SELECT auth.uid()) IS NOT NULL
    AND user_id = (SELECT auth.uid())
    AND attribution_mode IN ('anonymous', 'account')
    AND status = 'received'
    AND approved = false
    AND canonical_idea_id IS NULL
    AND receipt_hash ~ '^[0-9a-f]{64}$'
    AND ((contact IS NULL AND allow_contact = false) OR (contact IS NOT NULL AND allow_contact = true))
  );
CREATE POLICY fr_submissions_owner_read ON public.fr_submissions
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()));
REVOKE ALL ON public.fr_submissions FROM anon, authenticated;
GRANT INSERT (section, title, details, author, contact, language, user_id, attribution_mode, allow_contact, receipt_hash)
  ON public.fr_submissions TO anon, authenticated;
GRANT SELECT (id, section, title, details, author, contact, language, attribution_mode, allow_contact, status, canonical_idea_id, created_at)
  ON public.fr_submissions TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.fr_submissions_id_seq TO anon, authenticated;

CREATE OR REPLACE FUNCTION public.fr_submission_status(p_receipt text)
RETURNS TABLE(title text, status text, canonical_idea_id integer, created_at timestamptz)
LANGUAGE sql
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT s.title, s.status, s.canonical_idea_id, s.created_at
  FROM public.fr_submissions AS s
  WHERE s.receipt_hash = pg_catalog.encode(extensions.digest(p_receipt, 'sha256'), 'hex')
  LIMIT 1;
$$;
REVOKE ALL ON FUNCTION public.fr_submission_status(text) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.fr_submission_status(text) TO anon, authenticated;

ALTER TABLE public.fr_claims
  ADD COLUMN user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.fr_claims
  ALTER COLUMN user_id SET NOT NULL;
DROP POLICY IF EXISTS fr_claims_public_insert ON public.fr_claims;
CREATE POLICY fr_claims_authenticated_insert ON public.fr_claims
  FOR INSERT TO authenticated
  WITH CHECK (
    user_id = (SELECT auth.uid())
    AND status = 'pending'
  );
CREATE POLICY fr_claims_owner_read ON public.fr_claims
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()));
REVOKE ALL ON public.fr_claims FROM anon, authenticated;
GRANT INSERT (section, name, role, contact, proof_url, message, user_id)
  ON public.fr_claims TO authenticated;
GRANT SELECT (id, section, role, status, created_at)
  ON public.fr_claims TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.fr_claims_id_seq TO authenticated;

CREATE TABLE public.fr_profile_members (
  section text NOT NULL REFERENCES public.fr_sections(slug) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  member_email text NOT NULL,
  role text NOT NULL CHECK (role IN ('owner', 'admin', 'contributor')),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked')),
  invited_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  verified_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (section, user_id)
);
CREATE UNIQUE INDEX fr_profile_members_one_active_owner
  ON public.fr_profile_members (section)
  WHERE role = 'owner' AND status = 'active';
ALTER TABLE public.fr_profile_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY fr_profile_members_self_read ON public.fr_profile_members
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()));
REVOKE ALL ON public.fr_profile_members FROM anon, authenticated;
GRANT SELECT (section, user_id, role, status, verified_at, created_at)
  ON public.fr_profile_members TO authenticated;

CREATE TABLE public.fr_team_interests (
  id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  idea_id integer NOT NULL REFERENCES public.fr_ideas(id) ON DELETE CASCADE,
  section text NOT NULL REFERENCES public.fr_sections(slug) ON DELETE CASCADE,
  selected_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  selected_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
  revoked_at timestamptz,
  revoked_by uuid REFERENCES auth.users(id) ON DELETE SET NULL
);
CREATE UNIQUE INDEX fr_team_interests_one_active_per_member
  ON public.fr_team_interests (idea_id, selected_by)
  WHERE revoked_at IS NULL;
ALTER TABLE public.fr_team_interests ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.fr_team_interests FROM anon, authenticated;

CREATE OR REPLACE FUNCTION fanrank_private.sync_team_interest_count()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  v_idea_id integer;
  v_count integer;
BEGIN
  IF TG_OP = 'DELETE' THEN
    v_idea_id := OLD.idea_id;
  ELSE
    v_idea_id := NEW.idea_id;
  END IF;
  SELECT count(*)::integer INTO v_count
  FROM public.fr_team_interests AS ti
  JOIN public.fr_profile_members AS pm
    ON pm.section = ti.section AND pm.user_id = ti.selected_by
  WHERE ti.idea_id = v_idea_id
    AND ti.revoked_at IS NULL
    AND pm.status = 'active';

  UPDATE public.fr_ideas
  SET team_interest_count = COALESCE(v_count, 0),
      owner_pick = COALESCE(v_count, 0) > 0
  WHERE id = v_idea_id;
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION fanrank_private.sync_team_interest_count() FROM PUBLIC;
DROP TRIGGER IF EXISTS fr_team_interests_sync_count ON public.fr_team_interests;
CREATE TRIGGER fr_team_interests_sync_count
  AFTER INSERT OR UPDATE OF revoked_at OR DELETE ON public.fr_team_interests
  FOR EACH ROW EXECUTE FUNCTION fanrank_private.sync_team_interest_count();

CREATE OR REPLACE FUNCTION fanrank_private.sync_member_team_counts()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
  UPDATE public.fr_ideas AS i
  SET team_interest_count = COALESCE((
        SELECT count(*)::integer
        FROM public.fr_team_interests AS ti
        JOIN public.fr_profile_members AS pm
          ON pm.section = ti.section AND pm.user_id = ti.selected_by
        WHERE ti.idea_id = i.id
          AND ti.revoked_at IS NULL
          AND pm.status = 'active'
      ), 0),
      owner_pick = EXISTS (
        SELECT 1
        FROM public.fr_team_interests AS ti
        JOIN public.fr_profile_members AS pm
          ON pm.section = ti.section AND pm.user_id = ti.selected_by
        WHERE ti.idea_id = i.id
          AND ti.revoked_at IS NULL
          AND pm.status = 'active'
      )
  WHERE i.section = NEW.section;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION fanrank_private.sync_member_team_counts() FROM PUBLIC;
DROP TRIGGER IF EXISTS fr_profile_members_sync_team_counts ON public.fr_profile_members;
CREATE TRIGGER fr_profile_members_sync_team_counts
  AFTER UPDATE OF status ON public.fr_profile_members
  FOR EACH ROW
  WHEN (OLD.status IS DISTINCT FROM NEW.status)
  EXECUTE FUNCTION fanrank_private.sync_member_team_counts();

CREATE TABLE public.fr_profile_invites (
  id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
  section text NOT NULL REFERENCES public.fr_sections(slug) ON DELETE CASCADE,
  target_email text NOT NULL,
  role text NOT NULL CHECK (role IN ('admin', 'contributor')),
  token_hash text NOT NULL UNIQUE CHECK (token_hash ~ '^[0-9a-f]{64}$'),
  invited_by uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  expires_at timestamptz NOT NULL,
  accepted_at timestamptz,
  accepted_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX fr_profile_invites_one_active_target
  ON public.fr_profile_invites (section, target_email)
  WHERE accepted_at IS NULL AND revoked_at IS NULL;
ALTER TABLE public.fr_profile_invites ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.fr_profile_invites FROM anon, authenticated;

CREATE OR REPLACE FUNCTION public.fr_set_team_interest(p_idea_id integer, p_active boolean)
RETURNS TABLE(team_interest_count integer, active boolean)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  v_actor uuid := auth.uid();
  v_section text;
  v_count integer;
BEGIN
  IF v_actor IS NULL OR p_active IS NULL THEN
    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'Authenticated member required';
  END IF;

  SELECT i.section INTO v_section
  FROM public.fr_ideas AS i
  WHERE i.id = p_idea_id AND i.approved;
  IF v_section IS NULL THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'Published idea required';
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM public.fr_profile_members AS pm
    JOIN public.fr_sections AS s ON s.slug = pm.section
    WHERE pm.section = v_section
      AND pm.user_id = v_actor
      AND pm.status = 'active'
      AND s.verification_status = 'verified'
  ) THEN
    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'Verified team membership required';
  END IF;

  IF p_active THEN
    INSERT INTO public.fr_team_interests (idea_id, section, selected_by)
    VALUES (p_idea_id, v_section, v_actor)
    ON CONFLICT (idea_id, selected_by) WHERE revoked_at IS NULL DO NOTHING;
  ELSE
    UPDATE public.fr_team_interests
    SET revoked_at = CURRENT_TIMESTAMP, revoked_by = v_actor
    WHERE idea_id = p_idea_id
      AND selected_by = v_actor
      AND revoked_at IS NULL;
  END IF;

  SELECT i.team_interest_count INTO v_count
  FROM public.fr_ideas AS i
  WHERE i.id = p_idea_id;
  RETURN QUERY SELECT COALESCE(v_count, 0), EXISTS (
    SELECT 1 FROM public.fr_team_interests AS ti
    WHERE ti.idea_id = p_idea_id AND ti.selected_by = v_actor AND ti.revoked_at IS NULL
  );
END;
$$;

CREATE OR REPLACE FUNCTION public.fr_my_team_interests(p_section text)
RETURNS TABLE(idea_id integer)
LANGUAGE sql
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT ti.idea_id
  FROM public.fr_team_interests AS ti
  JOIN public.fr_profile_members AS pm
    ON pm.section = ti.section AND pm.user_id = ti.selected_by
  WHERE ti.section = p_section
    AND ti.selected_by = auth.uid()
    AND ti.revoked_at IS NULL
    AND pm.status = 'active';
$$;

CREATE OR REPLACE FUNCTION public.fr_create_profile_invite(p_section text, p_email text, p_role text)
RETURNS TABLE(invite_token text, expires_at timestamptz)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  v_actor uuid := auth.uid();
  v_actor_role text;
  v_email text := pg_catalog.lower(pg_catalog.btrim(p_email));
  v_token text;
  v_expires timestamptz := CURRENT_TIMESTAMP + interval '48 hours';
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'Authenticated member required';
  END IF;
  IF v_email !~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$' THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'Valid email required';
  END IF;
  IF p_role NOT IN ('admin', 'contributor') THEN
    RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'Allowed roles are admin and contributor';
  END IF;

  SELECT pm.role INTO v_actor_role
  FROM public.fr_profile_members AS pm
  JOIN public.fr_sections AS s ON s.slug = pm.section
  WHERE pm.section = p_section
    AND pm.user_id = v_actor
    AND pm.status = 'active'
    AND s.verification_status = 'verified';
  IF v_actor_role IS NULL OR v_actor_role = 'contributor' THEN
    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'Owner or admin required';
  END IF;
  IF v_actor_role = 'admin' AND p_role <> 'contributor' THEN
    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'Admins may only invite contributors';
  END IF;
  IF EXISTS (
    SELECT 1 FROM public.fr_profile_members AS pm
    WHERE pm.section = p_section
      AND pg_catalog.lower(pm.member_email) = v_email
      AND pm.status = 'active'
  ) THEN
    RAISE EXCEPTION USING ERRCODE = '23505', MESSAGE = 'This email is already an active member';
  END IF;

  UPDATE public.fr_profile_invites
  SET revoked_at = CURRENT_TIMESTAMP
  WHERE section = p_section
    AND target_email = v_email
    AND accepted_at IS NULL
    AND revoked_at IS NULL;

  v_token := pg_catalog.encode(extensions.gen_random_bytes(32), 'hex');
  INSERT INTO public.fr_profile_invites (section, target_email, role, token_hash, invited_by, expires_at)
  VALUES (
    p_section,
    v_email,
    p_role,
    pg_catalog.encode(extensions.digest(v_token, 'sha256'), 'hex'),
    v_actor,
    v_expires
  );
  RETURN QUERY SELECT v_token, v_expires;
END;
$$;

CREATE OR REPLACE FUNCTION public.fr_preview_profile_invite(p_token text)
RETURNS TABLE(section text, profile_name text, role text, expires_at timestamptz)
LANGUAGE sql
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT i.section, s.name, i.role, i.expires_at
  FROM public.fr_profile_invites AS i
  JOIN public.fr_sections AS s ON s.slug = i.section
  JOIN auth.users AS u ON u.id = auth.uid() AND u.email_confirmed_at IS NOT NULL
  WHERE i.token_hash = pg_catalog.encode(extensions.digest(p_token, 'sha256'), 'hex')
    AND i.target_email = pg_catalog.lower(u.email)
    AND i.accepted_at IS NULL
    AND i.revoked_at IS NULL
    AND i.expires_at > CURRENT_TIMESTAMP
  LIMIT 1;
$$;

CREATE OR REPLACE FUNCTION public.fr_accept_profile_invite(p_token text)
RETURNS TABLE(section text, role text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  v_actor uuid := auth.uid();
  v_email text;
  v_invite public.fr_profile_invites%ROWTYPE;
BEGIN
  IF v_actor IS NULL THEN
    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'Authenticated user required';
  END IF;
  SELECT pg_catalog.lower(u.email) INTO v_email
  FROM auth.users AS u
  WHERE u.id = v_actor AND u.email_confirmed_at IS NOT NULL;
  IF v_email IS NULL THEN
    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'Confirmed email required';
  END IF;

  SELECT * INTO v_invite
  FROM public.fr_profile_invites
  WHERE token_hash = pg_catalog.encode(extensions.digest(p_token, 'sha256'), 'hex')
  FOR UPDATE;
  IF NOT FOUND
    OR v_invite.accepted_at IS NOT NULL
    OR v_invite.revoked_at IS NOT NULL
    OR v_invite.expires_at <= CURRENT_TIMESTAMP
    OR v_invite.target_email <> v_email THEN
    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'Invitation is invalid';
  END IF;
  IF EXISTS (
    SELECT 1 FROM public.fr_profile_members AS pm
    WHERE pm.section = v_invite.section AND pm.user_id = v_actor AND pm.status = 'active'
  ) THEN
    RAISE EXCEPTION USING ERRCODE = '23505', MESSAGE = 'User is already an active member';
  END IF;

  INSERT INTO public.fr_profile_members (section, user_id, member_email, role, status, invited_by, verified_at, revoked_at)
  VALUES (v_invite.section, v_actor, v_email, v_invite.role, 'active', v_invite.invited_by, CURRENT_TIMESTAMP, NULL)
  ON CONFLICT (section, user_id) DO UPDATE
  SET member_email = EXCLUDED.member_email,
      role = EXCLUDED.role,
      status = 'active',
      invited_by = EXCLUDED.invited_by,
      verified_at = CURRENT_TIMESTAMP,
      revoked_at = NULL
  WHERE public.fr_profile_members.status = 'revoked';

  UPDATE public.fr_profile_invites
  SET accepted_at = CURRENT_TIMESTAMP, accepted_by = v_actor
  WHERE id = v_invite.id;
  RETURN QUERY SELECT v_invite.section, v_invite.role;
END;
$$;

CREATE OR REPLACE FUNCTION public.fr_profile_team(p_section text)
RETURNS TABLE(user_id uuid, member_email text, role text, status text, verified_at timestamptz, created_at timestamptz)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  v_role text;
BEGIN
  SELECT pm.role INTO v_role
  FROM public.fr_profile_members AS pm
  WHERE pm.section = p_section
    AND pm.user_id = auth.uid()
    AND pm.status = 'active';
  IF v_role NOT IN ('owner', 'admin') THEN
    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'Owner or admin required';
  END IF;
  RETURN QUERY
  SELECT pm.user_id, pm.member_email, pm.role, pm.status, pm.verified_at, pm.created_at
  FROM public.fr_profile_members AS pm
  WHERE pm.section = p_section AND pm.status = 'active'
  ORDER BY CASE pm.role WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END, pm.created_at;
END;
$$;

CREATE OR REPLACE FUNCTION public.fr_revoke_profile_member(p_section text, p_user_id uuid)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  v_actor uuid := auth.uid();
  v_actor_role text;
  v_target_role text;
BEGIN
  SELECT pm.role INTO v_actor_role
  FROM public.fr_profile_members AS pm
  WHERE pm.section = p_section AND pm.user_id = v_actor AND pm.status = 'active';
  SELECT pm.role INTO v_target_role
  FROM public.fr_profile_members AS pm
  WHERE pm.section = p_section AND pm.user_id = p_user_id AND pm.status = 'active'
  FOR UPDATE;
  IF v_actor_role NOT IN ('owner', 'admin') OR v_target_role IS NULL THEN
    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'Unauthorized team change';
  END IF;
  IF p_user_id = v_actor OR v_target_role = 'owner' THEN
    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'Owner transfer is required';
  END IF;
  IF v_actor_role = 'admin' AND v_target_role <> 'contributor' THEN
    RAISE EXCEPTION USING ERRCODE = '42501', MESSAGE = 'Admins may only revoke contributors';
  END IF;

  UPDATE public.fr_team_interests
  SET revoked_at = CURRENT_TIMESTAMP, revoked_by = v_actor
  WHERE section = p_section AND selected_by = p_user_id AND revoked_at IS NULL;
  UPDATE public.fr_profile_members
  SET status = 'revoked', revoked_at = CURRENT_TIMESTAMP
  WHERE section = p_section AND user_id = p_user_id;
END;
$$;

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

ALTER TABLE public.fr_events
  DROP CONSTRAINT IF EXISTS fr_events_event_check;
ALTER TABLE public.fr_events
  ADD CONSTRAINT fr_events_event_check
  CHECK (event IN (
    'page_view', 'search', 'profile_open', 'idea_open', 'idea_share', 'vote', 'submission',
    'section_request', 'claim_request', 'suggest_open', 'similar_vote', 'auth_open',
    'auth_link_requested', 'auth_signed_in', 'auth_signed_out', 'activity_open', 'team_interest',
    'team_invite_created'
  ));
DROP POLICY IF EXISTS fr_events_public_insert ON public.fr_events;
CREATE POLICY fr_events_public_insert ON public.fr_events
  FOR INSERT TO anon, authenticated
  WITH CHECK (
    char_length(event) <= 80
    AND (section IS NULL OR char_length(section) <= 120)
    AND (value IS NULL OR char_length(value) <= 180)
    AND (visitor IS NULL OR char_length(visitor) <= 100)
  );

CREATE OR REPLACE VIEW public.fr_ranking
WITH (security_invoker = true)
AS
SELECT
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
  i.team_interest_count
FROM public.fr_ideas AS i
WHERE i.approved = true;

CREATE OR REPLACE VIEW public.fr_sections_stats
WITH (security_invoker = true)
AS
SELECT
  s.slug,
  s.name,
  s.emoji,
  s.kind,
  s.tagline,
  s.tagline_es,
  count(i.id)::integer AS ideas,
  COALESCE(sum(i.origin_upvotes), 0)::integer AS reddit_upvotes,
  COALESCE(sum(i.web_votes), 0)::integer AS fan_votes,
  s.verification_status
FROM public.fr_sections AS s
LEFT JOIN public.fr_ideas AS i
  ON i.section = s.slug AND i.approved = true
GROUP BY s.slug;
GRANT SELECT ON public.fr_ranking, public.fr_sections_stats TO anon, authenticated;

-- A team heart is a capped aggregate signal, never a legacy "owner pick" override.
UPDATE public.fr_ideas
SET owner_pick = false
WHERE owner_pick IS DISTINCT FROM false;

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
  SET team_interest_count = COALESCE(v_count, 0)
  WHERE id = v_idea_id;

  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION fanrank_private.sync_team_interest_count() FROM PUBLIC;

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
      ), 0)
  WHERE i.section = NEW.section;
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION fanrank_private.sync_member_team_counts() FROM PUBLIC;

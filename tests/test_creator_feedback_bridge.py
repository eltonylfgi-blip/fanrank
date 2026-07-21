#!/usr/bin/env python3
"""Contrato del puente: creador autorizado -> cola privada -> buzón de revisión Codex."""

from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import tempfile
import unittest


FANRANK = Path(__file__).resolve().parents[1]
MADRE = FANRANK.parent.parent
OWNER_STUDIO = (FANRANK / "owner-studio.js").read_text(encoding="utf-8")
MIGRATION = (
    FANRANK
    / "supabase"
    / "migrations"
    / "20260721113000_fanrank_v22_creator_feedback_codex_bridge.sql"
).read_text(encoding="utf-8")
CREATOR_INTAKE = (
    FANRANK / "supabase" / "functions" / "fanrank-creator-feedback" / "index.ts"
).read_text(encoding="utf-8")
SPEC = spec_from_file_location("drenaje_feedback", MADRE / "WIDGETS" / "drenar_feedback_panel.py")
DRENAJE = module_from_spec(SPEC)
SPEC.loader.exec_module(DRENAJE)


class CreatorFeedbackBridgeTests(unittest.TestCase):
    def test_studio_only_opens_creator_feedback_to_verified_owner_or_admin(self):
        self.assertIn("function isProfileFeedbackManager()", OWNER_STUDIO)
        self.assertIn("function canSubmitFeedback()", OWNER_STUDIO)
        self.assertIn("window.membership.role === \"owner\" || window.membership.role === \"admin\"", OWNER_STUDIO)
        self.assertIn("window.secMeta.verification_status === \"verified\"", OWNER_STUDIO)
        self.assertIn("section:window.SECTION || null", OWNER_STUDIO)

    def test_database_keeps_creator_feedback_and_captures_private(self):
        self.assertIn("add column if not exists section", MIGRATION)
        self.assertIn("fr_owner_feedback_creator_insert", MIGRATION)
        self.assertIn("section is not null", MIGRATION)
        self.assertIn("member.role in ('owner', 'admin')", MIGRATION)
        self.assertIn("profile.verification_status = 'verified'", MIGRATION)
        self.assertIn("JWT-protected Edge Function", MIGRATION)
        self.assertIn('"fanrank-owner-feedback"', CREATOR_INTAKE)
        self.assertIn("admin.auth.getUser(token)", CREATOR_INTAKE)
        self.assertIn('profile.verification_status !== "verified"', CREATOR_INTAKE)
        self.assertIn('.in("role", ["owner", "admin"])', CREATOR_INTAKE)
        self.assertIn("admin.storage.from(BUCKET).upload", CREATOR_INTAKE)
        self.assertIn('"/functions/v1/fanrank-creator-feedback"', OWNER_STUDIO)

    def test_private_screenshot_is_signed_and_seen_only_after_the_buzon_receipt(self):
        calls = []

        def fake(url, headers, method="GET", payload=None, timeout=30):
            calls.append((url, method, payload))
            if method == "POST":
                return {"signedURL": "/object/sign/fanrank-owner-feedback/u-1/capture.png?token=test"}
            if method == "PATCH":
                return [{"id": 42}]
            return []

        signed = DRENAJE.signed_fanrank_screenshot("secret", "u-1/capture.png", fetcher=fake)
        self.assertTrue(signed.startswith(DRENAJE.SB_URL + "/storage/v1/object/sign/"))
        self.assertEqual(calls[0][2], {"expiresIn": DRENAJE.FANRANK_SCREENSHOT_TTL_SECONDS})

        marked = DRENAJE.mark_fanrank_seen(
            "secret", [42], now=datetime(2026, 7, 21, tzinfo=timezone.utc), fetcher=fake
        )
        self.assertEqual(marked, [42])
        self.assertIn("status=eq.new", calls[-1][0])
        self.assertEqual(calls[-1][2]["status"], "seen")

    def test_receipt_is_daily_append_only_and_contains_context_and_capture(self):
        row = {
            "id": 42,
            "section": "creator-profile",
            "page_path": "/fanrank/perfil/creator-profile",
            "zone": "hero",
            "message": "Haz el CTA más claro.",
            "priority": "high",
            "created_at": "2026-07-21T10:00:00+00:00",
            "screenshot_url": "https://signed.example/capture.png",
        }
        now = datetime(2026, 7, 21, 12, 0, tzinfo=timezone.utc).astimezone()
        with tempfile.TemporaryDirectory(prefix="fanrank-feedback-test-") as folder:
            path, first = DRENAJE.volcar_fanrank([row], now=now, buzon_dir=folder)
            _, second = DRENAJE.volcar_fanrank([row], now=now, buzon_dir=folder)
            content = path.read_text(encoding="utf-8")

        self.assertEqual(path.name, "DESDE_FANRANK_2026-07-21_creator-feedback.txt")
        self.assertEqual((first, second), (1, 2))
        self.assertEqual(content.count("DE: FanRank"), 1)
        self.assertEqual(content.count("--- TANDA "), 2)
        self.assertIn("creator-profile", content)
        self.assertIn("https://signed.example/capture.png", content)
        self.assertIn("Haz el CTA más claro.", content)


if __name__ == "__main__":
    unittest.main(verbosity=2)

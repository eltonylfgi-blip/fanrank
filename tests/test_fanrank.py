"""Repeatable checks for FanRank's static app and public Supabase boundary.

Run locally:
    python tests/test_fanrank.py
    python tests/test_fanrank.py --live

The live suite is read-only apart from deliberately invalid POST requests that
must be rejected by RLS policy. It never creates user or test data.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import struct
import subprocess
import sys
import unittest
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
HTML = INDEX.read_text(encoding="utf-8")
INVARIANTS_PATH = ROOT / "PRODUCT_INVARIANTS.json"
INVARIANTS = json.loads(INVARIANTS_PATH.read_text(encoding="utf-8"))
LOCAL_AGENT_CONTRACT = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
SOCIAL_CARD = ROOT / "social-card.png"
PROFILE_STUB_GENERATOR = ROOT / "tools" / "generate_profile_stubs.py"
PROFILE_STUB_ROOT = ROOT / "p"
TOP_PAGES_GENERATOR = ROOT / "tools" / "build_top_pages.py"
TOP_ROOT = ROOT / "top"
OWNER_JS_PATH = ROOT / "owner-studio.js"
OWNER_CSS_PATH = ROOT / "owner-studio.css"
OWNER_JS = OWNER_JS_PATH.read_text(encoding="utf-8")
OWNER_CSS = OWNER_CSS_PATH.read_text(encoding="utf-8")
DISCOVERY_MIGRATION = ROOT / "supabase" / "migrations" / "20260715152000_fanrank_v6_discovery_directory.sql"
DISCOVERY_SQL = DISCOVERY_MIGRATION.read_text(encoding="utf-8")
OWNER_MIGRATION = ROOT / "supabase" / "migrations" / "20260715160000_fanrank_v7_owner_studio.sql"
OWNER_SQL = OWNER_MIGRATION.read_text(encoding="utf-8")
PRO_MIGRATION = ROOT / "supabase" / "migrations" / "20260715170000_fanrank_v8_pro_pilot.sql"
PRO_SQL = PRO_MIGRATION.read_text(encoding="utf-8")
FAN_MEDIA_MIGRATION = ROOT / "supabase" / "migrations" / "20260715021357_fanrank_fan_profiles_media.sql"
FAN_MEDIA_SQL = FAN_MEDIA_MIGRATION.read_text(encoding="utf-8")
TEAM_STARS_MIGRATION = ROOT / "supabase" / "migrations" / "20260715183000_fanrank_v9_team_stars.sql"
TEAM_STARS_SQL = TEAM_STARS_MIGRATION.read_text(encoding="utf-8")
EVIDENCE_MIGRATION = ROOT / "supabase" / "migrations" / "20260715190000_fanrank_v10_evidence_links_telemetry.sql"
EVIDENCE_SQL = EVIDENCE_MIGRATION.read_text(encoding="utf-8")
TEAM_INBOX_MIGRATION = ROOT / "supabase" / "migrations" / "20260715193000_fanrank_v11_team_submission_inbox.sql"
TEAM_INBOX_SQL = TEAM_INBOX_MIGRATION.read_text(encoding="utf-8")
TOPICS_MIGRATION = ROOT / "supabase" / "migrations" / "20260716034000_fanrank_v12_profile_topics.sql"
CLAIM_INTEGRITY_MIGRATION = ROOT / "supabase" / "migrations" / "20260716043000_fanrank_v14_claim_integrity.sql"
CLAIM_INTEGRITY_SQL = CLAIM_INTEGRITY_MIGRATION.read_text(encoding="utf-8")
ALERTS_MIGRATION = ROOT / "supabase" / "migrations" / "20260716051732_fanrank_v16_localized_share_alerts.sql"
ALERTS_SQL = ALERTS_MIGRATION.read_text(encoding="utf-8") if ALERTS_MIGRATION.exists() else ""
ALERTS_INDEX_MIGRATION = ROOT / "supabase" / "migrations" / "20260716054800_fanrank_v16_milestone_fk_indexes.sql"
ALERTS_INDEX_SQL = ALERTS_INDEX_MIGRATION.read_text(encoding="utf-8") if ALERTS_INDEX_MIGRATION.exists() else ""
DUEL_EVENTS_MIGRATION = ROOT / "supabase" / "migrations" / "20260716222500_fanrank_v19_duel_events.sql"
DUEL_EVENTS_SQL = DUEL_EVENTS_MIGRATION.read_text(encoding="utf-8") if DUEL_EVENTS_MIGRATION.exists() else ""
MEDIA_INTAKE_PATH = ROOT / "supabase" / "functions" / "fanrank-feedback-intake" / "index.ts"
MEDIA_INTAKE = MEDIA_INTAKE_PATH.read_text(encoding="utf-8")
ALERTS_INTAKE_PATH = ROOT / "supabase" / "functions" / "fanrank-milestone-alerts" / "index.ts"
ALERTS_INTAKE = ALERTS_INTAKE_PATH.read_text(encoding="utf-8") if ALERTS_INTAKE_PATH.exists() else ""
ANDROID_PROMPT_PATH = ROOT / "docs" / "FANRANK_ANDROID_GEMINI_PROMPT.md"
ANDROID_PROMPT = ANDROID_PROMPT_PATH.read_text(encoding="utf-8")


def extract(pattern: str) -> str:
    match = re.search(pattern, HTML, re.DOTALL)
    if not match:
        raise AssertionError(f"Pattern not found: {pattern}")
    return match.group(1)


def extract_js_function(name: str) -> str:
    """Return one complete top-level JS function using balanced braces."""
    start = HTML.find(f"function {name}(")
    if start < 0:
        raise AssertionError(f"JavaScript function not found: {name}")
    opening = HTML.find("{", start)
    if opening < 0:
        raise AssertionError(f"Opening brace not found for JavaScript function: {name}")
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(opening, len(HTML)):
        char = HTML[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ('"', "'", "`"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return HTML[start:index + 1]
    raise AssertionError(f"Closing brace not found for JavaScript function: {name}")


SB_URL = extract(r'var SB_URL = "([^"]+)";')
SB_KEY = extract(r'var SB_KEY = "([^"]+)";')
EXPECTED_PROJECT_REF = "kopegamcjozrvmxruwdn"
EXPECTED_PUBLISHABLE_KEY = "sb_publishable_2NDyczKDwFCzNIWEMycRtw_yTnkUQAi"


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.label_targets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.append(str(values["id"]))
        if tag == "label" and values.get("for"):
            self.label_targets.append(str(values["for"]))


class StaticAppTests(unittest.TestCase):
    def test_durable_product_invariants_are_wired_into_code_and_agent_workflow(self) -> None:
        active_ids = {
            rule["id"] for rule in INVARIANTS["rules"] if rule["status"] == "active"
        }
        self.assertEqual(1, INVARIANTS["schema_version"])
        self.assertEqual("FanRank", INVARIANTS["product"])
        self.assertTrue(
            {
                "FR-INV-001",
                "FR-INV-002",
                "FR-INV-003",
                "FR-INV-004",
                "FR-INV-005",
                "FR-INV-007",
                "FR-INV-009",
            }.issubset(active_ids)
        )
        self.assertIn("PRODUCT_INVARIANTS.json", LOCAL_AGENT_CONTRACT)
        self.assertIn("tests/test_visual_regression.py", LOCAL_AGENT_CONTRACT)
        self.assertIn("git status --short", LOCAL_AGENT_CONTRACT)
        self.assertIn(r"INVARIANTES\verificar.py fanrank", LOCAL_AGENT_CONTRACT)
        self.assertNotRegex(
            HTML,
            r"[.]logo-fan,[.]rank-text\{[^}]*color:transparent",
        )
        self.assertIn('diamond:', HTML)
        self.assertIn('["◆","Impacto real verificado","impact"]', HTML)
        self.assertIn('["◆","Verified real-world impact","impact"]', HTML)

    def test_android_gemini_handoff_preserves_product_and_backend_boundaries(self) -> None:
        markers = [
            "## INICIO DEL PROMPT",
            "FanRank ♥",
            "FanRank ★",
            "organicScore = aiScore + min(fanHearts * 2, 20)",
            "FeatureFlag.NativeMediaUpload = false",
            "fr_sections_stats",
            "fr_ranking",
            "`ScreenViewed` → `page_view`",
            "ServerEventName",
            "No implementes cobros",
            "**1A · Esqueleto:**",
            "implementa **solo la Fase 1**",
            "## FIN DEL PROMPT",
        ]
        for marker in markers:
            self.assertIn(marker, ANDROID_PROMPT)
        self.assertNotIn("service_role=", ANDROID_PROMPT.lower())
        self.assertNotIn("supabase_anon_key=ey", ANDROID_PROMPT.lower())

    def test_utf8_and_mobile_document(self) -> None:
        self.assertIn('<meta charset="UTF-8">', HTML)
        self.assertIn('name="viewport"', HTML)
        self.assertIn("FanRank — the best ideas, ranked", HTML)
        self.assertNotIn("â€”", HTML)

        suggest_dialog = extract(r'<dialog id="suggest-dialog"[\s\S]*?<form id="submit-form"[^>]*>([\s\S]*?)</form>')
        self.assertEqual(1, suggest_dialog.count("<textarea"))
        self.assertIn('<input id="submit-details" type="hidden">', suggest_dialog)
        self.assertLess(
            suggest_dialog.index('id="submit-idea"'),
            suggest_dialog.index('id="submit-send"'),
            "The single send action must immediately follow the minimum composer.",
        )
        self.assertLess(
            suggest_dialog.index('id="submit-send"'),
            suggest_dialog.index('id="submit-advanced"'),
            "Optional metadata must not block the first submission action.",
        )
        self.assertIn('class="submit-bar quick-submit"', suggest_dialog)
        self.assertIn("margin:12px 0 0", HTML)
        self.assertIn("margin:10px 0 0", HTML)
        self.assertNotIn("margin:18px -24px", HTML)
        self.assertNotIn("margin:16px -18px", HTML)

    def test_critical_product_flows_are_wired(self) -> None:
        markers = {
            "universal search": 'id="global-search"',
            "profile discovery filters": 'id="directory-filters"',
            "multi-tag profile metadata": 'id="profile-tags"',
            "one-tap suggestion": 'data-quick-suggest=',
            "profile request": 'id="request-form"',
            "easy suggestion": 'id="suggest-open"',
            "idea submission": 'id="submit-form"',
            "similar ideas": 'id="similar-ideas"',
            "private contact": 'id="submit-contact"',
            "password account": 'id="auth-password"',
            "passwordless account": 'id="auth-magic"',
            "password recovery": 'id="auth-recover"',
            "private activity": 'id="activity-dialog"',
            "private screenshot intake": 'id="media-box"',
            "feedback category": 'id="category-legend"',
            "fan impact profile": 'id="fan-profile-form"',
            "public fan profile": 'id="fan-public-view"',
            "password rotation": 'id="password-change-form"',
            "profile claim": 'id="claim-form"',
            "verified team management": 'id="team-dialog"',
            "secure invitation acceptance": 'id="invite-dialog"',
            "fan vote": 'data-vote="',
            "verified team stars": 'data-team-star="',
            "shareable idea": "navigator.share",
            "product telemetry": 'postRow("fr_claims"',
            "event sink": 'fr_events',
            "bilingual UI": "var T = {",
            "owner studio bundle": 'owner-studio.js?v=10',
            "Pro pilot": 'id="pro-form"',
        }
        missing = [name for name, marker in markers.items() if marker not in HTML]
        self.assertEqual([], missing)

    def test_ids_are_unique_and_labels_point_to_fields(self) -> None:
        parser = StructureParser()
        parser.feed(HTML)
        duplicates = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
        missing_targets = sorted(set(parser.label_targets) - set(parser.ids))
        self.assertEqual([], duplicates)
        self.assertEqual([], missing_targets)
        self.assertGreaterEqual(len(parser.ids), 80)

    def test_inline_javascript_parses(self) -> None:
        result = subprocess.run(
            [
                "node",
                "-e",
                (
                    "const h=require('fs').readFileSync(process.argv[1],'utf8');"
                    "const m=h.match(/<script>([\\s\\S]*?)<\\/script>/);"
                    "if(!m)throw new Error('No inline script');"
                    "new (require('vm').Script)(m[1]);"
                ),
                str(INDEX),
            ],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)

        owner_result = subprocess.run(
            ["node", "--check", str(OWNER_JS_PATH)],
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(0, owner_result.returncode, owner_result.stderr or owner_result.stdout)

    def test_public_key_is_scoped_to_expected_anon_project(self) -> None:
        self.assertEqual(f"https://{EXPECTED_PROJECT_REF}.supabase.co", SB_URL)
        if SB_KEY.startswith("sb_publishable_"):
            # New Supabase publishable keys are intentionally opaque, not JWTs. Pin the
            # known public key so an accidental project/key swap still fails statically.
            self.assertEqual(EXPECTED_PUBLISHABLE_KEY, SB_KEY)
            self.assertNotIn("sb_secret_", SB_KEY)
            return
        pieces = SB_KEY.split(".")
        self.assertEqual(3, len(pieces))
        padded = pieces[1] + "=" * (-len(pieces[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        self.assertEqual("supabase", payload["iss"])
        self.assertEqual(EXPECTED_PROJECT_REF, payload["ref"])
        self.assertEqual("anon", payload["role"])

    def test_accessibility_and_resilience_guards_exist(self) -> None:
        markers = [
            'class="skip-link"',
            ':focus-visible',
            'prefers-reduced-motion:reduce',
            'aria-live="polite"',
            'min-height:44px',
            'rel="noopener noreferrer"',
            "function esc(value)",
            "function safeUrl(value)",
            "prefers-reduced-motion:reduce",
            'aria-pressed="',
            'aria-live="polite"',
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])

    def test_launch_copy_and_spam_guards_match_product_reality(self) -> None:
        markers = [
            "¡PARA TODOS!",
            'var APP_URL = "https://eltonylfgi-blip.github.io/fanrank/";',
            'var url = new URL(local ? APP_URL : location.origin + location.pathname);',
            "UNVERIFIED FAN PROFILE",
            "PERFIL DE FANS NO VERIFICADO",
            'validTiming("submit-website","fr_last_submission",30000)',
            'validTiming("claim-website","fr_last_claim",60000)',
            'location.hostname === "127.0.0.1"',
            "var receiptHash = await hashReceipt(receipt)",
            "allow_contact",
            'url.hash = "invite="',
            "function armCelestialAudio",
            "function playCelestialChime",
            "logoFloatIdle",
            "logoFloatActive",
            "tagPop",
            'source_votes:"apoyo en la fuente"',
            'source_votes_help:"Apoyo recibido en la publicación original; no son corazones de FanRank."',
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])
        self.assertNotIn("Search any <b>game, creator or company</b>", HTML)
        self.assertNotIn("Verified team picks score 100", HTML)
        self.assertNotIn("puntúan 100", HTML)
        self.assertNotIn("logoShakeSmooth", HTML)

    def test_discovery_directory_is_practical_and_data_driven(self) -> None:
        html_markers = [
            '["featured","✦","Destacados"]',
            '["creators-es","🎙️","Creadores · España"]',
            '["games","🎮","Videojuegos"]',
            '["companies","🏢","Empresas"]',
            '["social","💬","Redes sociales"]',
            '["ai","✨","IA"]',
            'sectionTags(item).slice(0,3)',
            'sectionUrl(item.slug,true)',
            'id="empty-suggest"',
            'cleanUrl.searchParams.delete("suggest")',
        ]
        self.assertEqual([], [marker for marker in html_markers if marker not in HTML])

        for slug in ("rubius", "orslok", "ibai", "roblox", "discord", "x-twitter", "chatgpt", "claude"):
            self.assertIn(f"('{slug}'", DISCOVERY_SQL)
        self.assertIn("array['spain','streamer','youtuber','tiktoker']", DISCOVERY_SQL)
        self.assertIn("with (security_invoker = true)", DISCOVERY_SQL)

    def test_passwordless_primary_auth_and_contextual_brand_have_safe_guards(self) -> None:
        self.assertIn("authClient.auth.signInWithOtp({", HTML)
        self.assertIn("options:{emailRedirectTo:authRedirectUrl(),shouldCreateUser:true}", HTML)
        self.assertIn('id="auth-magic"', HTML)
        self.assertLess(HTML.index('id="auth-magic"'), HTML.index('id="auth-password-panel"'))
        self.assertIn("authClient.auth.signInWithPassword({email:email,password:password})", HTML)
        current_password_input = extract(r'(<input id="auth-password"[^>]+>)')
        self.assertIn('autocomplete="current-password"', current_password_input)
        self.assertIn("required", current_password_input)
        self.assertNotIn("minlength=", current_password_input)
        self.assertIn('|| !password){', HTML)
        self.assertNotIn("password.length < 8", HTML)
        self.assertIn("authClient.auth.updateUser({password:nextPassword})", HTML)
        new_password_input = extract(r'(<input id="password-change-input"[^>]+>)')
        self.assertIn('autocomplete="new-password"', new_password_input)
        self.assertIn('minlength="12"', new_password_input)
        self.assertIn("if(REDUCED || !audioArmed || !audioContext || chimePlayed)", HTML)
        self.assertIn("setTimeout(function(){chimePlayed = false;},9000)", HTML)
        self.assertIn("brand-mark-heart", HTML)
        self.assertIn("brand-mark-team", HTML)
        self.assertIn('secMeta.verification_status === "verified"', HTML)
        self.assertIn('document.body.classList.toggle("team-mode",teamMode)', HTML)
        self.assertIn("M60 5 73 40 111 42", HTML)

    def test_private_media_fan_profiles_and_consent_are_wired_end_to_end(self) -> None:
        html_markers = [
            'accept="image/png,image/jpeg,image/webp"',
            'byId("quick-composer").addEventListener("paste"',
            'byId("media-box").addEventListener("drop"',
            'evidenceCount() + next.length > 3',
            'file.size > 5 * 1024 * 1024',
            '"/functions/v1/fanrank-feedback-intake"',
            'category_requested:categoryRequested',
            'ai_training_consent:!!(session && byId("submit-training-consent").checked)',
            'callRpc("fr_set_submission_ai_consent"',
            'callRpc("fr_upsert_my_fan_profile"',
            'callRpc("fr_public_fan_profile"',
            'profile.top_suggestions.slice(0,3)',
        ]
        self.assertEqual([], [marker for marker in html_markers if marker not in HTML])
        self.assertNotIn('accept="video/', HTML)

        sql_markers = [
            "ai_training_consent boolean not null default false",
            "attachment_count between 0 and 3",
            "new.category_final := new.category_requested",
            "new.classification_method := 'user'",
            "new.classification_method := 'rules_v1'",
            "create table public.fr_submission_attachments",
            "owner_user_id = (select auth.uid())",
            "'fanrank-feedback-private'",
            "public = false",
            "create table public.fr_fan_profiles",
            "where p.handle = pg_catalog.lower(pg_catalog.btrim(p_handle))",
            "and p.is_public = true",
            "limit 5",
            "least(100, pg_catalog.round(2 * s.points))",
        ]
        self.assertEqual([], [marker for marker in sql_markers if marker.lower() not in FAN_MEDIA_SQL.lower()])
        self.assertIn("No storage.objects policy is created", FAN_MEDIA_SQL)

        intake_markers = [
            "const MAX_FILES = 3",
            "const MAX_FILE_BYTES = 5 * 1024 * 1024",
            'admin.auth.getUser(token)',
            'admin.rpc("fr_register_media_intake"',
            "detectMime(new Uint8Array",
            '.from("fr_submission_attachments")',
            'review_status: duplicate ? "duplicate" : "quarantined"',
            "public: false",
        ]
        self.assertEqual([], [marker for marker in intake_markers if marker not in MEDIA_INTAKE])
        self.assertNotIn("video/", MEDIA_INTAKE)

    def test_supporting_links_are_safe_private_and_anonymous_capable(self) -> None:
        html_markers = [
            'id="evidence-link-input"',
            'function normalizeEvidenceLink(value)',
            'parsed.protocol !== "https:"',
            '"https://www.youtube.com/watch?v=" + videoId',
            '"https://i.ytimg.com/vi/" + videoId + "/hqdefault.jpg"',
            'target="_blank" rel="noopener noreferrer"',
            'referrerpolicy="no-referrer"',
            'evidence_links:pendingLinks.map',
            'formData.append("links",item.canonicalUrl)',
        ]
        self.assertEqual([], [marker for marker in html_markers if marker not in HTML])
        self.assertNotIn('accept="video/', HTML)
        self.assertNotIn("<iframe", HTML.lower())

        sql_markers = [
            "evidence_links text[] not null default '{}'::text[]",
            "cardinality(p_links) > 3",
            "attachment_count + cardinality(evidence_links) <= 3",
            "grant insert (evidence_links) on public.fr_submissions to anon, authenticated",
            "the server never fetches them",
        ]
        self.assertEqual([], [marker for marker in sql_markers if marker.lower() not in EVIDENCE_SQL.lower()])

        intake_markers = [
            "function normalizeEvidenceLink(value: string)",
            'form.getAll("links")',
            "files.length + evidenceLinks.length > MAX_FILES",
            "evidence_links: evidenceLinks",
            "links: evidenceLinks.length",
        ]
        self.assertEqual([], [marker for marker in intake_markers if marker not in MEDIA_INTAKE])
        self.assertNotIn("oembed", MEDIA_INTAKE.lower())
        self.assertNotIn("fetch(", MEDIA_INTAKE)

        parser_source = HTML[
            HTML.index("function normalizeEvidenceLink(value)"):
            HTML.index("function renderPendingLinks()")
        ]
        cases = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ?t=10",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://m.youtube.com/live/dQw4w9WgXcQ",
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
            "https://example.com/proof?q=1#fragment",
        ]
        invalid = [
            "http://youtu.be/dQw4w9WgXcQ",
            "javascript:alert(1)",
            "https://user:pass@example.com/x",
            "https://youtube.com.evil.test/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/short",
        ]
        node_program = parser_source + "\n" + (
            f"const good={json.dumps(cases)}.map(normalizeEvidenceLink);"
            f"const bad={json.dumps(invalid)}.map(normalizeEvidenceLink);"
            "console.log(JSON.stringify({good,bad}));"
        )
        result = subprocess.run(["node", "-e", node_program], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        parsed = json.loads(result.stdout)
        self.assertTrue(all(parsed["good"]))
        self.assertTrue(all(value is None for value in parsed["bad"]))
        self.assertTrue(all(item["canonicalUrl"].startswith("https://") for item in parsed["good"]))
        self.assertEqual("https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg", parsed["good"][0]["thumbnailUrl"])

    def test_team_inbox_migration_has_exact_youtube_and_auth_boundaries(self) -> None:
        normalized = re.sub(r"\s+", " ", TEAM_INBOX_SQL.lower()).strip()
        youtube_markers = [
            "create or replace function public.fr_valid_evidence_links(p_links text[])",
            "position('youtube' in pg_catalog.lower(item)) > 0",
            "position('youtu.be' in pg_catalog.lower(item)) > 0",
            "item !~ '^https://www[.]youtube[.]com/watch[?]v=[A-Za-z0-9_-]{11}$'",
        ]
        self.assertEqual([], [marker for marker in youtube_markers if marker not in TEAM_INBOX_SQL])
        self.assertIn(
            "revoke all on function public.fr_valid_evidence_links(text[]) from public, anon, authenticated;",
            normalized,
        )
        self.assertIn(
            "grant execute on function public.fr_valid_evidence_links(text[]) to anon, authenticated, service_role;",
            normalized,
        )

        inbox_markers = [
            "create or replace function public.fr_team_submission_inbox(",
            "security definer",
            "set search_path = ''",
            "v_actor uuid := auth.uid()",
            "if v_actor is null then",
            "a.status = 'active'",
            "m.section = v_section",
            "m.role in ('owner', 'admin')",
            "m.status = 'active'",
            "s.verification_status = 'verified'",
            "case when submission.allow_contact then submission.author else null end as author",
            "case when submission.allow_contact then submission.contact else null end as contact",
            "where submission.section = v_section",
            "least(greatest(coalesce(p_limit, 50), 1), 50)",
        ]
        self.assertEqual([], [marker for marker in inbox_markers if marker not in normalized])
        self.assertIn(
            "revoke all on function public.fr_team_submission_inbox(text, integer) from public, anon, authenticated;",
            normalized,
        )
        self.assertIn(
            "grant execute on function public.fr_team_submission_inbox(text, integer) to authenticated;",
            normalized,
        )
        self.assertNotRegex(
            normalized,
            r"grant execute on function public[.]fr_team_submission_inbox\(text, integer\) to [^;]*anon",
        )

    def test_composer_target_media_and_accessibility_are_explicit(self) -> None:
        markers = [
            'class="quick-composer" id="quick-composer"',
            'id="submit-target-context"',
            'id="submit-target-context" role="group" aria-labelledby="submit-target-label"',
            'id="submit-target-label" for="submit-target"',
            'id="submit-idea-label" for="submit-idea"',
            '<details class="composer-media" id="media-box">',
            '<label class="field-label" id="evidence-link-label" for="evidence-link-input">',
            'byId("evidence-link-label").textContent = tx("evidence_link_label")',
            'byId("logo").setAttribute("aria-label",tx(teamMode ? "logo_team_label" : "logo_public_label"))',
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])
        composer = extract(r'<section class="quick-composer"[\s\S]*?>([\s\S]*?)</details>\s*</section>')
        self.assertLess(composer.index('id="submit-target"'), composer.index('id="submit-idea"'))
        self.assertLess(composer.index('id="submit-idea"'), composer.index('id="media-box"'))
        self.assertNotIn('<details class="composer-media" id="media-box" open>', HTML)
        dialog = extract(r'<dialog id="suggest-dialog"[\s\S]*?>([\s\S]*?)</dialog>')
        self.assertLess(dialog.index('id="submit-privacy-note"'), dialog.index('id="submit-send"'))
        self.assertIn('media_title:"Añadir una imagen o enlace (opcional)"', HTML)
        self.assertIn('idea_help:"Pega aquí una captura con Ctrl+V. Los vídeos se añaden por enlace."', HTML)
        self.assertIn('submit_privacy_account:"Pública con tu perfil Fan"', HTML)
        self.assertIn('submit_privacy_contact:"Nombre y contacto privados · revisión privada"', HTML)
        self.assertIn('var key = mode === "account" ? "submit_privacy_account"', HTML)
        self.assertIn('byId("submit-target-label").removeAttribute("for")', HTML)
        self.assertRegex(HTML, r"[.]category-option span\{[^}]*min-height:44px")
        self.assertRegex(HTML, r"[.]media-remove\{[^}]*width:44px;height:44px")

        translated_keys = (
            "skip_to_content",
            "global_rank_label",
            "profile_filters_label",
            "ranking_label",
            "top_three_label",
            "logo_public_label",
            "logo_team_label",
        )
        for key in translated_keys:
            with self.subTest(key=key):
                self.assertGreaterEqual(HTML.count(f'{key}:"'), 2)
                self.assertIn(key, HTML[HTML.index("function applyStaticText()"):])

        accessibility_consumers = (
            'byId("skip-link").textContent = tx("skip_to_content")',
            'byId("home-rank-tabs").setAttribute("aria-label",tx("global_rank_label"))',
            'byId("directory-filters").setAttribute("aria-label",tx("profile_filters_label"))',
            'byId("profile-rank-tabs").setAttribute("aria-label",tx("ranking_label"))',
            'byId("podium").setAttribute("aria-label",tx("top_three_label"))',
        )
        self.assertEqual([], [marker for marker in accessibility_consumers if marker not in HTML])

    def test_qa_mode_survives_every_internal_url_helper(self) -> None:
        self.assertIn('byId("logo").href = homeUrl();', HTML)
        self.assertIn('byId("fan-public-back").href = homeUrl();', HTML)
        function_names = (
            "normalizeLanguage",
            "persistentUrl",
            "profileDefaultLanguage",
            "setUrlLanguage",
            "homeUrl",
            "fanProfileUrl",
            "fanSuggestionUrl",
            "teamInviteUrl",
            "sectionUrl",
            "profileStubUrl",
            "appIdeaUrl",
            "ideaUrl",
        )
        functions = "\n".join(extract_js_function(name) for name in function_names)
        node_program = "\n".join(
            [
                'var TELEMETRY_DISABLED=true;',
                'var LANG="es";',
                'var URL_LANGUAGE="es";',
                'var SAVED_LANGUAGE=null;',
                'var SECTION="orslok";',
                'var APP_URL="https://eltonylfgi-blip.github.io/fanrank/";',
                'var sections=[{slug:"orslok",default_language:"es"}];',
                (
                    'var location={origin:"https://eltonylfgi-blip.github.io",pathname:"/fanrank/",'
                    'search:"?s=orslok&lang=es&qa=1",'
                    'href:"https://eltonylfgi-blip.github.io/fanrank/?s=orslok&lang=es&qa=1"};'
                ),
                functions,
                (
                    'console.log(JSON.stringify({'
                    'home:homeUrl(),section:sectionUrl("orslok",true),'
                    'appIdea:appIdeaUrl({section:"orslok",id:17}),'
                    'idea:ideaUrl({section:"orslok",id:17}),fan:fanProfileUrl("tony"),'
                    'fanIdea:fanSuggestionUrl({section:"orslok",idea_id:17}),'
                    'invite:teamInviteUrl("invite-token")'
                    '}));'
                ),
            ]
        )
        result = subprocess.run(
            ["node", "-e", node_program],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        urls = json.loads(result.stdout)
        parsed = {
            name: urllib.parse.urlsplit(urllib.parse.urljoin("https://eltonylfgi-blip.github.io", value))
            for name, value in urls.items()
        }
        for name, url in parsed.items():
            with self.subTest(name=name):
                self.assertEqual(["1"], urllib.parse.parse_qs(url.query).get("qa"))
        self.assertEqual(["orslok"], urllib.parse.parse_qs(parsed["section"].query).get("s"))
        self.assertEqual(["1"], urllib.parse.parse_qs(parsed["section"].query).get("suggest"))
        self.assertEqual("/fanrank/", parsed["appIdea"].path)
        self.assertEqual(["17"], urllib.parse.parse_qs(parsed["idea"].query).get("idea"))
        self.assertEqual("/fanrank/p/orslok/", parsed["idea"].path)
        self.assertEqual(["tony"], urllib.parse.parse_qs(parsed["fan"].query).get("fan"))
        self.assertEqual(["17"], urllib.parse.parse_qs(parsed["fanIdea"].query).get("idea"))
        self.assertEqual("invite=invite-token", parsed["invite"].fragment)

    def test_language_resolution_and_share_links_are_explicit(self) -> None:
        for marker in (
            "function normalizeLanguage(value)",
            "function resolveLanguage(urlLanguage,savedLanguage,profileLanguage,browserLanguage)",
            "function profileDefaultLanguage(slug)",
            "function setUrlLanguage(url,language)",
            "function buildSharePayload(kind,item,language)",
            'id="share-dialog"',
            'id="share-language-es"',
            'id="share-language-en"',
            'id="share-copy-all"',
            'id="share-native"',
            'id="share-copy-link"',
        ):
            self.assertIn(marker, HTML)

        functions = "\n".join(
            extract_js_function(name)
            for name in ("normalizeLanguage", "resolveLanguage")
        )
        node_program = "\n".join(
            [
                functions,
                "console.log(JSON.stringify([",
                'resolveLanguage("en","es","es","es"),',
                'resolveLanguage(null,"en","es","es"),',
                'resolveLanguage(null,null,"es","en"),',
                'resolveLanguage(null,null,"auto","es"),',
                'resolveLanguage(null,null,null,"fr")',
                "]));",
            ]
        )
        result = subprocess.run(
            ["node", "-e", node_program], cwd=ROOT, capture_output=True,
            text=True, check=False, timeout=10,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        self.assertEqual(["en", "en", "es", "es", "en"], json.loads(result.stdout))

        for language in ("es", "en"):
            node_program = "\n".join(
                [
                    "var TELEMETRY_DISABLED=true;",
                    f'var LANG="{language}";',
                    'var URL_LANGUAGE="' + language + '";',
                    'var SAVED_LANGUAGE=null;',
                    'var SECTION="orslok";',
                    'var APP_URL="https://eltonylfgi-blip.github.io/fanrank/";',
                    'var sections=[{slug:"orslok",default_language:"es"}];',
                    (
                        'var location={origin:"https://eltonylfgi-blip.github.io",pathname:"/fanrank/",'
                        'search:"?s=orslok&lang=' + language + '&qa=1",'
                        'href:"https://eltonylfgi-blip.github.io/fanrank/?s=orslok&lang=' + language + '&qa=1"};'
                    ),
                    "\n".join(
                        extract_js_function(name)
                        for name in (
                            "normalizeLanguage", "persistentUrl", "profileDefaultLanguage",
                            "setUrlLanguage", "homeUrl", "sectionUrl", "profileStubUrl",
                            "appIdeaUrl", "ideaUrl",
                            "fanProfileUrl", "fanSuggestionUrl", "teamInviteUrl",
                        )
                    ),
                    (
                        'console.log(JSON.stringify(['
                        'homeUrl(),sectionUrl("orslok",true),appIdeaUrl({section:"orslok",id:17}),'
                        'ideaUrl({section:"orslok",id:17}),'
                        'fanProfileUrl("tony"),fanSuggestionUrl({section:"orslok",idea_id:17}),'
                        'teamInviteUrl("invite-token")'
                        ']));'
                    ),
                ]
            )
            result = subprocess.run(
                ["node", "-e", node_program], cwd=ROOT, capture_output=True,
                text=True, check=False, timeout=10,
            )
            self.assertEqual(0, result.returncode, result.stderr or result.stdout)
            for raw_url in json.loads(result.stdout):
                parsed_url = urllib.parse.urlsplit(
                    urllib.parse.urljoin("https://eltonylfgi-blip.github.io", raw_url)
                )
                query = urllib.parse.parse_qs(parsed_url.query)
                self.assertEqual([language], query.get("lang"), raw_url)
                self.assertEqual(["1"], query.get("qa"), raw_url)

        mobile_cta = extract_js_function("setupMobileCta")
        self.assertIn('byId("suggest-open")', mobile_cta)
        self.assertIn('byId("home-suggest")', mobile_cta)
        self.assertIn("threshold:.5", mobile_cta)
        self.assertNotIn('document.querySelector(".suggest-cta")', mobile_cta)
        self.assertRegex(HTML, r"[.]top-btn [.]lang-flag\{[^}]*width:31px;[^}]*height:20px")
        self.assertIn(".dialog-card{width:100%;max-width:100%", HTML)
        self.assertNotIn(".dialog-card{width:100vw", HTML)

    def test_milestone_alert_preferences_are_private_idempotent_and_honest(self) -> None:
        ui_markers = (
            'id="submit-alert-optin"',
            'id="submit-alert-fields"',
            'id="submit-alert-email" type="email"',
            'name="submit-alert-milestone"',
            'value="hearts_100"',
            'value="above_average"',
            'value="ai_90"',
            'value="official_star"',
            '"/functions/v1/fanrank-milestone-alerts"',
            "function milestoneAlertRequest()",
            "function subscribeMilestoneAlerts(receipt,request)",
            'alert_beta_note:"',
        )
        self.assertEqual([], [marker for marker in ui_markers if marker not in HTML])
        self.assertLess(HTML.index('id="submit-send"'), HTML.index('id="submit-alert-optin"'))
        self.assertLess(HTML.index('id="submit-advanced"'), HTML.index('id="submit-alert-optin"'))
        self.assertIn('alert_title:"Prepara avisos de logros futuros (beta)"', HTML)
        self.assertIn("todavía no se envían correos", HTML)
        self.assertNotIn('alert_title:"Avísame', HTML)

        sql_markers = (
            "add column default_language text not null default 'auto'",
            "create table fanrank_private.fr_milestone_subscriptions",
            "create table fanrank_private.fr_milestone_outbox",
            "alter table fanrank_private.fr_milestone_subscriptions force row level security",
            "alter table fanrank_private.fr_milestone_outbox force row level security",
            "unique (subscription_id, idea_id, milestone)",
            "create or replace function public.fr_register_milestone_subscription",
            "grant execute on function public.fr_register_milestone_subscription(text, text, text[], text) to service_role",
            "status text not null default 'blocked_provider'",
            "section_row.default_language",
            "'hearts_100'",
            "'above_average'",
            "'ai_90'",
            "'official_star'",
        )
        self.assertEqual([], [marker for marker in sql_markers if marker not in ALERTS_SQL.lower()])
        self.assertNotRegex(
            ALERTS_SQL.lower(),
            r"grant\s+(?:select|insert|update|delete|all).*fr_milestone_(?:subscriptions|outbox).*\b(?:anon|authenticated)\b",
        )
        for index_name in (
            "fr_milestone_subscriptions_user_idx",
            "fr_milestone_outbox_idea_idx",
        ):
            self.assertIn(index_name, ALERTS_INDEX_SQL)

        edge_markers = (
            'const DEFAULT_ORIGINS = ["https://eltonylfgi-blip.github.io"]',
            'admin.rpc("fr_register_milestone_subscription"',
            'receipt: string',
            'email: string',
            'delivery: "pending_provider"',
            'Cache-Control": "no-store"',
        )
        self.assertEqual([], [marker for marker in edge_markers if marker not in ALERTS_INTAKE])
        self.assertNotIn("console.log", ALERTS_INTAKE)

    def test_owner_verification_cta_is_honest_secondary_and_measurable(self) -> None:
        markers = [
            'id="home-owner-verify"',
            'owner_verify_kicker:"FOR CREATORS AND COMPANIES"',
            'owner_verify_kicker:"PARA CREADORES Y EMPRESAS"',
            'owner_verify_title:"Do you represent a creator or company?"',
            'owner_verify_title:"\u00bfRepresentas a un creador o una empresa?"',
            'owner_verify_copy:"Reclama el perfil para organizar ideas y valorar propuestas."',
            'owner_verify_action:"Request verification"',
            'owner_verify_action:"Solicitar verificaci\u00f3n"',
            '"El famoso o su equipo valora ideas"',
            '"The creator or team rates ideas"',
            'Así la IA aprende su criterio sin sustituir los corazones de los fans.',
            'document.querySelector(".global-rank-block").after(byId("stats"))',
            'byId("section-view").before(byId("stats"))',
            'sendEvent("owner_cta_open"',
            'params.get("claim") === "1"',
            'searchParams.set("claim","1")',
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])
        self.assertLess(HTML.index('id="home-suggest"'), HTML.index('id="home-owner-verify"'))
        self.assertLess(HTML.index('class="global-rank-block"'), HTML.index('id="home-owner-verify"'))
        self.assertLess(HTML.index('id="home-owner-verify"'), HTML.index('class="directory-block"'))
        self.assertRegex(HTML, r"[.]owner-verify-cta\{[^}]*background:transparent")
        self.assertRegex(HTML, r"[.]owner-verify-cta\{[^}]*min-height:48px")

    def test_verified_profiles_reject_new_or_duplicate_claims(self) -> None:
        client_markers = [
            'item.verification_status !== "verified"',
            'if(secMeta.verification_status === "verified")',
            'if(!secMeta || secMeta.verification_status === "verified")',
            'claim_already_verified:"This profile is already verified.',
            'claim_already_verified:"Este perfil ya est\u00e1 verificado.',
        ]
        self.assertEqual([], [marker for marker in client_markers if marker not in HTML])
        self.assertGreaterEqual(HTML.count('secMeta.verification_status === "verified"'), 3)

        normalized = re.sub(r"\s+", " ", CLAIM_INTEGRITY_SQL.lower()).strip()
        server_markers = [
            "create unique index if not exists fr_claims_one_pending_per_user_section_idx",
            "where status = 'pending'",
            "create or replace function fanrank_private.fr_validate_pending_claim_target()",
            "verification_status is distinct from 'verified'",
            "create trigger fr_claims_validate_pending_target",
            "drop policy if exists fr_claims_authenticated_insert",
            "user_id = (select auth.uid())",
        ]
        self.assertEqual([], [marker for marker in server_markers if marker not in normalized])

    def test_profile_topics_have_server_caps_safe_management_and_real_ui(self) -> None:
        sql = TOPICS_MIGRATION.read_text(encoding="utf-8")
        normalized = re.sub(r"\s+", " ", sql.lower()).strip()
        sql_markers = [
            "create table public.fr_profile_topics",
            "topic_tier in ('normal', 'pro', 'business', 'plus')",
            "when 'normal' then 5",
            "when 'pro' then 20",
            "when 'business' then 100",
            "when 'plus' then 200",
            "alter table public.fr_profile_topics enable row level security",
            "with (security_invoker = true)",
            "create or replace function public.fr_upsert_profile_topic",
            "create or replace function public.fr_archive_profile_topic",
            "create or replace function public.fr_set_idea_topic",
            "set search_path = ''",
            "for update",
            "status = 'active'",
            "verified profile owner or administrator required",
            "grant execute on function public.fr_upsert_profile_topic",
            "to authenticated",
            "topic_id bigint",
            "references public.fr_profile_topics(id)",
            "add column if not exists topic_id",
        ]
        self.assertEqual([], [marker for marker in sql_markers if marker not in normalized])
        self.assertNotRegex(
            normalized,
            r"grant execute on function public[.]fr_(upsert_profile_topic|archive_profile_topic|set_idea_topic)[^;]*anon",
        )
        self.assertNotIn("checkout", normalized)
        self.assertNotIn("stripe", normalized)

        html_markers = [
            'id="profile-topics"',
            'id="topic-manager"',
            'id="submit-topic-field"',
            'function loadProfileTopics()',
            'function renderProfileTopics()',
            'callRpc("fr_upsert_profile_topic"',
            'callRpc("fr_archive_profile_topic"',
            'callRpc("fr_set_idea_topic"',
            'topic_id:currentSuggestionTopic()',
            'formData.append("topic_id"',
            'topic_limit',
            'topic_active_count',
        ]
        self.assertEqual([], [marker for marker in html_markers if marker not in HTML])
        intake_markers = [
            'const topicId = optionalPositiveIntegerField(form, "topic_id")',
            "topic_id: topicId",
        ]
        self.assertEqual([], [marker for marker in intake_markers if marker not in MEDIA_INTAKE])

    def test_mobile_suggestion_cta_never_competes_with_inline_cta(self) -> None:
        markers = [
            "body.profile-live.mobile-cta-ready .mobile-suggest",
            "body.home-live.mobile-cta-ready .mobile-suggest",
            "body.suggest-dialog-open .mobile-suggest",
            "new IntersectionObserver",
            'document.body.classList.toggle("mobile-cta-ready",entries[0].intersectionRatio < .5)',
            'document.body.classList.add("suggest-dialog-open")',
            'document.body.classList.remove("suggest-dialog-open")',
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])

    def test_every_emitted_event_is_allowed_and_qa_is_excluded(self) -> None:
        emitted = set(re.findall(r'sendEvent\("([a-z0-9_]+)"', HTML + "\n" + OWNER_JS))
        event_sql = EVIDENCE_SQL + "\n" + (TOPICS_MIGRATION.read_text(encoding="utf-8") if TOPICS_MIGRATION.exists() else "") + "\n" + ALERTS_SQL + "\n" + DUEL_EVENTS_SQL
        blocks = re.findall(
            r"add constraint fr_events_event_check\s+check \(event in \((.*?)\)\);",
            event_sql,
            re.DOTALL | re.IGNORECASE,
        )
        self.assertTrue(blocks)
        allowed = set(re.findall(r"'([a-z0-9_]+)'", blocks[-1]))
        self.assertEqual(set(), emitted - allowed)
        self.assertIn('var TELEMETRY_DISABLED = params.get("qa") === "1";', HTML)
        self.assertIn("if(TELEMETRY_DISABLED ||", HTML)

    def test_password_recovery_covers_magic_link_accounts(self) -> None:
        markers = [
            "authClient.auth.resetPasswordForEmail(email,{redirectTo:recoveryRedirectUrl()})",
            'event === "PASSWORD_RECOVERY"',
            "await openPasswordRecovery()",
            'byId("password-change-panel").open = true',
            'params.get("recover") === "1"',
            'cleanRecoveryUrl.searchParams.delete("code")',
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])
        self.assertNotRegex(HTML, r"(?i)password\s*[:=]\s*['\"][^'\"]+['\"]")

    def test_owner_studio_is_private_practical_and_fair(self) -> None:
        markers = [
            'fr_platform_admins?select=user_id,role,status',
            'window.authClient.storage.from("fanrank-owner-feedback").upload',
            'window.postRow("fr_owner_feedback"',
            'window.postRow("fr_profile_requests"',
            'window.callRpc("fr_admin_set_profile_image"',
            'window.postRow("fr_promotion_requests"',
            'data-feedback-zone',
            'capturePastedImage',
            'Nunca promociona una idea ni compra votos, nota IA o posición orgánica.',
            'unverified:"Perfil creado por fans · pendiente de verificar"',
            'class="profile-monogram"',
            'identity.querySelector(".profile-identity-detail").appendChild(tags)',
            'identity.appendChild(claimBar)',
            'claimBar.classList.toggle("hidden",verified)',
        ]
        self.assertEqual([], [marker for marker in markers if marker not in OWNER_JS])
        self.assertIn("body.fr-zone-picking [data-feedback-zone]", OWNER_CSS)
        self.assertIn('.profile-identity{display:grid', OWNER_CSS)
        self.assertIn('.profile-claim{grid-area:claim', OWNER_CSS)
        self.assertIn("@media(prefers-reduced-motion:reduce)", OWNER_CSS)
        self.assertNotIn("sb_secret_", OWNER_JS)

    def test_owner_database_boundary_is_rls_enforced(self) -> None:
        markers = [
            "create table public.fr_platform_admins",
            "create table public.fr_owner_feedback",
            "create table public.fr_profile_requests",
            "create table public.fr_promotion_requests",
            "alter table public.fr_owner_feedback enable row level security",
            "alter table public.fr_profile_requests enable row level security",
            "alter table public.fr_promotion_requests enable row level security",
            "organic_rank_unchanged boolean not null default true check (organic_rank_unchanged = true)",
            "('fanrank-owner-feedback', 'fanrank-owner-feedback', false",
            "('fanrank-profile-images', 'fanrank-profile-images', true",
            "create or replace function public.fr_admin_set_profile_image",
            "revoke all on function public.fr_admin_set_profile_image",
            "'fanrank', 'FanRank', '⚡', 'company'",
        ]
        self.assertEqual([], [marker for marker in markers if marker.lower() not in OWNER_SQL.lower()])
        self.assertNotIn("eltonylfgi", OWNER_SQL.lower())
        self.assertNotRegex(OWNER_SQL, r"(?i)password\s*[:=]\s*['\"]")

    def test_pro_pilot_is_measurable_private_and_cannot_buy_rank(self) -> None:
        html_markers = [
            'price:"149 €"',
            'price:"449 €"',
            'price:"999 €"',
            "aportaciones válidas / mes",
            'callRpc("fr_request_pro_pilot"',
            "p_feedback_band:byId(\"pro-volume\").value",
            "p_cadence:byId(\"pro-cadence\").value",
            "p_goal:goal",
            "pagar nunca cambia el ranking orgánico",
        ]
        self.assertEqual([], [marker for marker in html_markers if marker not in HTML])
        sql_markers = [
            "create table public.fr_pro_requests",
            "alter table public.fr_pro_requests enable row level security",
            "create or replace function public.fr_request_pro_pilot",
            "v_actor uuid := auth.uid()",
            "revoke all on function public.fr_request_pro_pilot",
            "organic_rank_unchanged boolean not null default true check (organic_rank_unchanged = true)",
            "fr_promotion_requests_profile_only_check",
            "check (placement = 'profile' and idea_id is null)",
        ]
        self.assertEqual([], [marker for marker in sql_markers if marker.lower() not in PRO_SQL.lower()])
        self.assertNotIn('data-promote-idea=', HTML)
        self.assertNotIn('openPromotion("idea"', OWNER_JS)

    def test_fan_offers_measure_interest_without_selling_organic_position(self) -> None:
        offer_markers = [
            'id="fan-offers"',
            'id="profile-club"',
            'fan_founder_5_once',
            'profile_club_499_month',
            'idea_sponsor_concept_interest',
            'idea_sponsor_launch_interest',
            'idea_sponsor_periodic_interest',
            'offer_seen:fan_offers',
            'offer_seen:profile_club',
            'offer_seen:receipt_sponsor',
            'Fan fundador',
            '5 €',
            'pago único',
            'ANUNCIO PAGADO',
            'Todavía no se cobra',
            'profile_club_cta:"Me interesa este Club"',
            'fan_offers_contract_label:"Contrato de confianza del pago"',
            'byId("fan-offers-contract").setAttribute("aria-label",tx("fan_offers_contract_label"))',
            'function recordOfferInterest(offerId,button)',
            'function offerInterestKey(offerId,button)',
            'function observeOfferPlacement(node,eventName,value)',
            'new IntersectionObserver',
            'data-offer-context="',
            'sendEvent(eventName,{section:SECTION || suggestionSection || null,value:offerId})',
        ]
        self.assertEqual([], [marker for marker in offer_markers if marker not in HTML])
        trust_markers = [
            'No compra posición, nota IA, corazones, estrellas, respuesta ni un número fingido.',
            'La suscripción abre un canal; no compra posición, respuesta ni aprobación.',
            'No cambia la nota IA ni la posición orgánica.',
        ]
        self.assertEqual([], [marker for marker in trust_markers if marker not in HTML])
        self.assertNotIn('data-promote-idea=', HTML)
        self.assertNotIn('openPromotion("idea"', OWNER_JS)
        for function_name in ("rankScore", "officialTeamScore", "sortedIdeas"):
            body = extract(rf"function {function_name}\([^)]*\)\{{([\s\S]*?)\n\}}")
            self.assertNotRegex(body, r"(?i)offer|sponsor|paid|payment|interest")

    def test_founder_price_inversion_and_entity_support_are_interest_only(self) -> None:
        founder_markers = [
            'badge:"SOLO 500"',
            'name:"Fan fundador",price:"5 €",suffix:"pago único"',
            'recibirás tu número de Fundador: #N de 500',
            'id:"fan_founder_5_once",label:"Me interesa por 5 €"',
            'name:"Founding Fan",price:"€5",suffix:"one-time payment"',
            'Founder number: #N of 500',
        ]
        self.assertEqual([], [marker for marker in founder_markers if marker not in HTML])
        self.assertNotIn("fan_founder_15_once", HTML)
        entity_markers = [
            'id="entity-support"',
            'data-offer-interest="entity_support_15_or_open"',
            'entity_support_title:"Apoyo de entidad"',
            'entity_support_price:"15 € o aportación libre"',
            'entity_support_note:"Prueba de interés · Todavía no se cobra."',
            'offer_seen:entity_support',
            'recordOfferInterest("entity_support_15_or_open"',
        ]
        self.assertEqual([], [marker for marker in entity_markers if marker not in HTML])
        self.assertIn(
            'pro_pilot_note:"Piloto de equipo · 199 € durante 14 días · solo interés, todavía no cobra"',
            HTML,
        )
        self.assertNotIn('id="entity-support-amount"', HTML)
        self.assertNotRegex(HTML, r"(?i)founder_(count|remaining)|fundadores?\s+restantes")

    def test_team_signal_is_limited_and_not_a_public_identity_leak(self) -> None:
        rank_body = extract(r"function rankScore\(item\)\{([\s\S]*?)\n\}")
        self.assertIn("Math.min(Number(item.web_votes || 0) * 2,20)", rank_body)
        self.assertNotIn("team_", rank_body)
        self.assertNotIn("owner_star", rank_body)
        self.assertIn('sortMode === "team"', HTML)
        self.assertIn("function officialTeamScore(item)", HTML)
        self.assertIn("fr_set_team_star", HTML)
        self.assertIn("fr_set_team_star_cap", HTML)
        self.assertIn("team_member_star_cap", HTML)
        self.assertIn('data-team-star="', HTML)
        public_rating_body = extract(r"function teamRatingHtml\(item\)\{([\s\S]*?)\n\}")
        self.assertNotIn("member_email", public_rating_body)
        self.assertNotIn("selected_by", public_rating_body)
        # La barra de reclamar sigue escondiendose en un perfil verificado (mismo
        # comportamiento; ahora via isClaimedProfile, la unica fuente de "reclamado").
        # OJO: esconder la BARRA ya no esconde el aviso legal -> vive fuera (FR-INV-010).
        self.assertIn(
            'document.querySelector(".claim-bar").classList.toggle("hidden",isClaimedProfile(secMeta))',
            HTML,
        )

        sql_markers = [
            "team_member_star_cap in (1, 3)",
            "star_value between 1 and 5",
            "create or replace function public.fr_set_team_star",
            "create or replace function public.fr_my_team_stars",
            "create or replace function public.fr_set_team_star_cap",
            "and s.verification_status = 'verified'",
            "and pm.status = 'active'",
            "and pm.role = 'owner'",
            "grant execute on function public.fr_set_team_star(integer, integer) to authenticated",
            "with (security_invoker = true)",
            "excluded from organic rank",
        ]
        self.assertEqual([], [marker for marker in sql_markers if marker.lower() not in TEAM_STARS_SQL.lower()])
        self.assertNotRegex(TEAM_STARS_SQL, r"(?i)password\s*[:=]\s*['\"]")

    def test_anonymous_submission_contract_matches_the_private_queue(self) -> None:
        self.assertIn('postRow("fr_submissions",submissionPayload)', HTML)
        self.assertIn("function submissionTextParts(value)", HTML)
        self.assertIn("var targetSection = currentSuggestionSection();", HTML)
        self.assertIn("section:targetSection,title:textParts.title,", HTML)
        self.assertIn("details:textParts.details", HTML)
        self.assertIn('identityMode === "contact" ? byId("submit-contact").value.trim() : ""', HTML)
        self.assertIn('session && identityMode === "account" ? "account" : "anonymous"', HTML)
        self.assertIn('headers:{"Prefer":"return=minimal"}', HTML)
        self.assertNotIn("section_slug:SECTION", HTML)

    def test_home_activation_is_universal_ranked_compact_and_accessible(self) -> None:
        markers = [
            "Improve what you use and follow.",
            "Mejora lo que usas y sigues.",
            'id="home-suggest"',
            'id="submit-target"',
            "function currentSuggestionSection()",
            "function populateSuggestionTargets()",
            'data-home-rank="ai"',
            'data-home-rank="fans"',
            'aria-controls="trending"',
            'id="trending" role="tabpanel"',
            'function activateHomeRank(tab,focusTab)',
            '["ArrowLeft","ArrowRight","Home","End"]',
            'data-home-vote="',
            '.home-vote.voted[disabled]',
            'trend-rank-number',
            'var compact = index > 2;',
            'idea_more:"More details and actions"',
            'idea_more:"Detalles y acciones"',
            'id="fan-value-title"',
            'id="home-profile-cta"',
            'id="directory-more"',
            'var initialLimit = window.matchMedia("(max-width:560px)").matches ? 3 : 6;',
            'var familiar = ["rubius","brawl-stars","discord"',
            "scroll-snap-type:x mandatory",
            '.trend-card{flex:0 0 min(360px,82%)',
            'data-fanrank-logo',
            '<span class="rank-text">RANK</span>',
            'class="rank-podium"',
            "podium-step",
            "rank-trophy",
            "flag-view-gb",
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])
        self.assertLess(HTML.index('id="home-suggest"'), HTML.index('class="global-rank-block"'))
        self.assertLess(HTML.index('class="global-rank-block"'), HTML.index('class="directory-block"'))
        self.assertNotIn('content="Ranked Brawl Stars', HTML)
        self.assertNotIn("will-change:transform", HTML)
        self.assertIn('byId("lang-flag").setAttribute("data-flag"', HTML)
        self.assertIn('if(SECTION){renderProfile();renderSimilarIdeas();}else{renderTrending();renderSimilarIdeas();}', HTML)
        render_sections = extract(r"function renderSections\(\)\{([\s\S]*?)\n\}\nfunction trendingIdeas")
        render_trending = extract(r"function renderTrending\(\)\{([\s\S]*?)\n\}\nfunction loadHome")
        self.assertIn('class="trend-card rank-\' + (index+1) + \'"', render_trending)
        self.assertIn('class="home-vote \' + (voted ? "voted" : "") + \'"', render_trending)
        self.assertIn('aria-label="\' + esc(voted ? tx("home_voted_aria",ideaTitle(item)) : tx("home_vote_aria",ideaTitle(item)))', render_trending)
        self.assertIn('moreButton.classList.toggle("hidden"', render_sections)
        self.assertNotIn("moreButton", render_trending)

    def test_activation_clarity_matches_the_public_product_contract(self) -> None:
        markers = [
            'search_label:"Find who or what you want to suggest something to"',
            'search_label:"Busca a qui\u00e9n o qu\u00e9 quieres sugerirle"',
            'kind_labels:{creator:"Content creator"',
            'kind_labels:{creator:"Creador de contenido"',
            'influencer:"Influencer"',
            '["tag:influencer","#","Influencer"]',
            '["tag:streamer","#","Streamer"]',
            'var socialCreator = ["streamer","youtuber","tiktoker"].some',
            'directoryMode.indexOf("tag:") === 0',
            'var selectedTag = directoryMode.slice(4);',
            'data-sort="balanced"',
            'id="tab-balanced"',
            'var sortMode = "balanced";',
            'if(sortMode === "balanced")',
            'else if(sortMode === "ai")',
            'claim_bar_title_named:function(name)',
            'tx("claim_bar_title_named",secMeta.name)',
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])
        self.assertRegex(HTML, r"[.]logo-art\{[^}]*max-width:calc\(100vw - 24px\)[^}]*overflow:visible")
        self.assertRegex(HTML, r"[.]logo-fan,[.]rank-text\{[^}]*overflow:visible")
        self.assertRegex(HTML, r"[.]rank-podium\{[^}]*top:[.]84em")
        self.assertRegex(HTML, r"[.]rank-trophy\{[^}]*width:1[.]12em;height:1[.]12em")
        self.assertRegex(
            HTML,
            r"@media \(max-width:560px\)\{[\s\S]*?[.]logo-art\{[^}]*--logo-size:clamp\(48px,13[.]6vw,54px\)",
        )
        self.assertEqual(1, HTML.count('<span class="rank-text">RANK</span>'))
        self.assertNotIn('class="rank-letter', HTML)
        self.assertNotIn('class="rank-place', HTML)
        self.assertIn('viewBox="7 5 66 78"', HTML)
        self.assertLess(HTML.index('id="home-suggest"'), HTML.index('id="directory-filters"'))

        sorted_ideas = extract(r"function sortedIdeas\(source\)\{([\s\S]*?)\n\}")
        self.assertIn('return rankScore(b)-rankScore(a)', sorted_ideas)
        self.assertIn('return Number(b.ai_score)-Number(a.ai_score)', sorted_ideas)
        self.assertIn('return Number(b.web_votes)-Number(a.web_votes)', sorted_ideas)

    def test_celestial_logo_respects_user_control_without_a_rectangular_shine_slab(self) -> None:
        markers = [
            "starBloom",
            "trophyFloat",
            "document.addEventListener(\"pointerdown\",armCelestialAudio",
            "byId(\"logo\").addEventListener(\"pointerenter\"",
            "byId(\"logo\").addEventListener(\"pointermove\"",
            'window.matchMedia("(hover:hover) and (pointer:fine)").matches',
            "if(REDUCED || !audioArmed",
            "chimePlayed",
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])
        self.assertNotIn(".logo:after{", HTML)
        self.assertNotIn("@keyframes logoShine", HTML)
        self.assertNotIn(".logo:hover:after", HTML)

    def test_profile_sharing_has_a_clean_measurable_referral_loop(self) -> None:
        markers = [
            '<link rel="canonical" href="https://eltonylfgi-blip.github.io/fanrank/">',
            '<title>FanRank &mdash; las mejores ideas, ordenadas</title>',
            '<meta name="description" content="Vota lo que tu creador, juego o empresa favorita deber&#237;a mejorar &mdash; o deja tu idea en 10 segundos. Gratis, sin registro.">',
            '<meta property="og:title" content="FanRank &mdash; las mejores ideas, ordenadas">',
            '<meta property="og:description" content="Vota lo que tu creador, juego o empresa favorita deber&#237;a mejorar &mdash; o deja tu idea en 10 segundos. Gratis, sin registro.">',
            '<meta property="og:locale" content="es_ES">',
            '<meta property="og:locale:alternate" content="en_US">',
            '<meta property="og:image" content="https://eltonylfgi-blip.github.io/fanrank/social-card.png?v=3">',
            '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="630">',
            '<meta name="twitter:card" content="summary_large_image">',
            '<meta name="twitter:title" content="FanRank &mdash; las mejores ideas, ordenadas">',
            '<meta name="twitter:description" content="Vota lo que tu creador, juego o empresa favorita deber&#237;a mejorar &mdash; o deja tu idea en 10 segundos. Gratis, sin registro.">',
            '<meta name="twitter:image" content="https://eltonylfgi-blip.github.io/fanrank/social-card.png?v=3">',
            'id="profile-share"',
            'id="profile-share-text"',
            "function referralSource()",
            "var REFERRAL_SOURCES = {fan_share:true,idea_share:true,reddit:true,discord:true,x:true,whatsapp:true};",
            "function withReferral(url,source)",
            "function profileShareUrl(language)",
            "function buildSharePayload(kind,item,language)",
            'withReferral(ideaUrl(item,selectedLanguage),"idea_share")',
            'recordShareAction("copy_all")',
            'recordShareAction("copy_link")',
            'sendEvent("page_view",{section:SECTION || null,value:referralSource()})',
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])
        self.assertIn("return REFERRAL_SOURCES[source] ? source : null;", HTML)

        card = SOCIAL_CARD.read_bytes()
        self.assertEqual(b"\x89PNG\r\n\x1a\n", card[:8])
        self.assertEqual((1200, 630), struct.unpack(">II", card[16:24]))
        self.assertGreater(len(card), 50_000)

    def test_profile_share_payload_uses_the_loaded_top_three_with_a_255_char_budget(self) -> None:
        functions = "\n".join(
            extract_js_function(name)
            for name in (
                "rankScore",
                "officialTeamScore",
                "sortedIdeas",
                "localizedIdeaTitle",
                "truncateShareTitle",
                "buildProfileShareText",
            )
        )
        node_program = "\n".join(
            [
                'var sortMode="balanced";',
                'var ideas=[];',
                functions,
                'var fixture=[',
                '{id:2,title:"Second long request that should remain useful for fans",title_es:"Segunda petición larga que debe seguir siendo útil",ai_score:80,web_votes:1,origin_upvotes:0},',
                '{id:3,title:"Third curiosity request that deliberately leaves a gap",title_es:"Tercera petición que deja deliberadamente curiosidad",ai_score:70,web_votes:1,origin_upvotes:0},',
                '{id:1,title:"First request",title_es:"Primera petición",ai_score:95,web_votes:8,origin_upvotes:0}',
                '];',
                'console.log(JSON.stringify({',
                'es:buildProfileShareText("Orslok","es",fixture),',
                'en:buildProfileShareText("Orslok","en",fixture),',
                'fallbackEs:buildProfileShareText("Orslok","es",fixture.slice(0,2)),',
                'fallbackEn:buildProfileShareText("Orslok","en",fixture.slice(0,2))',
                '}));',
            ]
        )
        result = subprocess.run(
            ["node", "-e", node_program], cwd=ROOT, capture_output=True,
            text=True, encoding="utf-8", check=False, timeout=10,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertLessEqual(len(payload["es"]), 255)
        self.assertLessEqual(len(payload["en"]), 255)
        self.assertIn("Lo que los fans más piden a Orslok ahora mismo:", payload["es"])
        self.assertIn("1) Primera petición", payload["es"])
        self.assertRegex(payload["es"], r"(?m)^3\) .+…$")
        self.assertIn("What Orslok fans want most right now:", payload["en"])
        self.assertIn("¿Qué debería hacer Orslok? Deja tu idea en 10s:", payload["fallbackEs"])
        self.assertIn("What should Orslok do next? Add your idea in 10s:", payload["fallbackEn"])

    def test_share_dialog_exposes_human_x_and_whatsapp_intents(self) -> None:
        markers = (
            'id="share-x"',
            'id="share-whatsapp"',
            'target="_blank" rel="noopener"',
            "function buildShareIntentUrls(payload)",
            'recordShareAction("intent_x")',
            'recordShareAction("intent_whatsapp")',
        )
        self.assertEqual([], [marker for marker in markers if marker not in HTML])

        node_program = "\n".join(
            [
                'var location={origin:"https://eltonylfgi-blip.github.io"};',
                extract_js_function("withReferral"),
                extract_js_function("buildShareIntentUrls"),
                'console.log(JSON.stringify(buildShareIntentUrls({text:"Top real & útil",url:"https://eltonylfgi-blip.github.io/fanrank/p/orslok/?lang=es&ref=fan_share"})));',
            ]
        )
        result = subprocess.run(
            ["node", "-e", node_program], cwd=ROOT, capture_output=True,
            text=True, encoding="utf-8", check=False, timeout=10,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        intents = json.loads(result.stdout)
        x_query = urllib.parse.parse_qs(urllib.parse.urlsplit(intents["x"]).query)
        whatsapp_query = urllib.parse.parse_qs(urllib.parse.urlsplit(intents["whatsapp"]).query)
        self.assertEqual(["Top real & útil"], x_query.get("text"))
        self.assertEqual(["x"], urllib.parse.parse_qs(urllib.parse.urlsplit(x_query["url"][0]).query).get("ref"))
        self.assertIn("Top real & útil", whatsapp_query["text"][0])
        self.assertEqual(["whatsapp"], urllib.parse.parse_qs(urllib.parse.urlsplit(whatsapp_query["text"][0].split()[-1]).query).get("ref"))

    def test_profile_stubs_have_unique_og_and_safe_query_preserving_redirects(self) -> None:
        self.assertTrue(PROFILE_STUB_GENERATOR.exists())
        generator = PROFILE_STUB_GENERATOR.read_text(encoding="utf-8")
        for marker in (
            "fr_sections_stats?select=slug,name,default_language",
            "fr_ranking?select=id,section,title,title_es,ai_score,web_votes,origin_upvotes",
            "def render_stub(profile: dict, top_ideas: list[dict]) -> str:",
            'PRESERVED_QUERY_KEYS = ("idea", "ref", "lang", "qa")',
        ):
            self.assertIn(marker, generator)

        stubs = sorted(PROFILE_STUB_ROOT.glob("*/index.html"))
        self.assertGreaterEqual(len(stubs), 10)
        for stub in stubs:
            with self.subTest(slug=stub.parent.name):
                slug = stub.parent.name
                raw = stub.read_text(encoding="utf-8")
                canonical = f"https://eltonylfgi-blip.github.io/fanrank/p/{slug}/"
                self.assertIn(f'<link rel="canonical" href="{canonical}">', raw)
                self.assertIn(f'<meta property="og:url" content="{canonical}">', raw)
                self.assertIn('<meta property="og:title" content="Ideas para ', raw)
                self.assertIn('<meta name="twitter:card" content="summary_large_image">', raw)
                self.assertIn('social-card.png?v=2', raw)
                self.assertIn('["idea","ref","lang","qa"]', raw)
                self.assertIn('location.replace("/fanrank/?" + target.toString())', raw)
                self.assertIn(f'<noscript><a href="/fanrank/?s={slug}">', raw)

        self.assertIn("function profileStubUrl(slug,language,ideaId)", HTML)
        self.assertIn("function appIdeaUrl(item,language)", HTML)
        self.assertIn("return profileStubUrl(item.section,language,item.id);", HTML)
        self.assertIn("return withReferral(profileStubUrl(SECTION,language,null),\"fan_share\");", HTML)
        self.assertIn('href="\' + esc(appIdeaUrl(item)) + \'"', HTML)
        self.assertIn("location.href = appIdeaUrl(matches.ideas[0]);", HTML)


def api_request(path: str, method: str = "GET", body: dict | None = None) -> tuple[int, str]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "apikey": SB_KEY,
        "Content-Type": "application/json",
    }
    if method == "POST" and not path.startswith("rpc/"):
        headers["Prefer"] = "return=minimal"
    request = urllib.request.Request(
        f"{SB_URL}/rest/v1/{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8")


class V18UsabilityTests(unittest.TestCase):
    """v18 'nadie entra en vano': teaser del top en directorio, wow al votar,
    skeleton de carga y preconnect. Protege el pedido de Tony del 16-jul."""

    def test_preconnect_to_supabase(self) -> None:
        self.assertIn('rel="preconnect" href="https://kopegamcjozrvmxruwdn.supabase.co"', HTML)

    def test_directory_top_idea_teaser(self) -> None:
        self.assertIn("topIdeaBySection", HTML)
        self.assertIn('class="sec-top"', HTML)
        self.assertRegex(HTML, r"[.]sec-top\{[^}]*text-overflow:ellipsis")

    def test_vote_wow_and_first_vote_nudge(self) -> None:
        self.assertIn("heart-burst", HTML)
        self.assertIn("fr_vote_nudge", HTML)
        self.assertEqual(2, HTML.count("vote_nudge:"), "vote_nudge debe existir en EN y ES")

    def test_loading_skeleton_with_reduced_motion(self) -> None:
        self.assertIn('class="skeleton-grid" aria-hidden="true"', HTML)
        self.assertIn("skeletonShimmer", HTML)
        self.assertRegex(
            HTML,
            r"@media \(prefers-reduced-motion:reduce\)\{[.]skeleton-card,[.]heart-burst\{animation:none\}\}",
        )


class V19EngagementTests(unittest.TestCase):
    """v19: Duelo de ideas (votos reales por parejas) + arranque instantáneo con caché."""

    def test_duel_overlay_markup(self) -> None:
        self.assertIn('id="duel-overlay"', HTML)
        self.assertIn('id="duel-a"', HTML)
        self.assertIn('id="duel-b"', HTML)
        self.assertIn('class="duel-vs"', HTML)

    def test_duel_uses_real_votes_and_telemetry(self) -> None:
        self.assertIn("vote(id,card);", HTML)
        self.assertIn('sendEvent("duel_pick"', HTML)
        self.assertIn('sendEvent("duel_open"', HTML)

    def test_duel_i18n_in_both_languages(self) -> None:
        self.assertEqual(2, HTML.count("duel_button:"), "duel_button debe existir en EN y ES")
        self.assertEqual(2, HTML.count("duel_empty:"), "duel_empty debe existir en EN y ES")

    def test_home_cache_stale_while_revalidate(self) -> None:
        self.assertIn("fr_home_cache_v1", HTML)
        self.assertIn("writeHomeCache", HTML)
        self.assertIn("readHomeCache", HTML)

    def test_duel_respects_reduced_motion(self) -> None:
        self.assertRegex(HTML, r"@media \(prefers-reduced-motion:reduce\)\{[.]duel-launch,[.]duel-card\{transition:none\}\}")


class LiveBoundaryTests(unittest.TestCase):
    def test_public_directory_and_rankings_are_readable(self) -> None:
        status, raw = api_request(
            "fr_sections_stats?select=slug,name,kind,tags,featured_rank,ideas,recent_ideas,fan_votes,verification_status,team_member_star_cap,topic_tier,topic_limit,topic_active_count,default_language"
        )
        self.assertEqual(200, status, raw)
        sections = json.loads(raw)
        brawl = next(row for row in sections if row["slug"] == "brawl-stars")
        self.assertEqual("unverified", brawl["verification_status"])
        self.assertEqual(["mobile", "supercell"], brawl["tags"])

        by_slug = {row["slug"]: row for row in sections}
        self.assertTrue({"rubius", "orslok", "ibai", "roblox", "discord", "x-twitter", "chatgpt", "claude"}.issubset(by_slug))
        self.assertEqual("creator", by_slug["rubius"]["kind"])
        self.assertTrue({"spain", "streamer", "youtuber", "tiktoker"}.issubset(by_slug["rubius"]["tags"]))
        self.assertEqual("game", by_slug["roblox"]["kind"])
        self.assertEqual("social", by_slug["discord"]["kind"])
        self.assertEqual("ai", by_slug["chatgpt"]["kind"])
        self.assertEqual("company", by_slug["fanrank"]["kind"])
        self.assertEqual("verified", by_slug["fanrank"]["verification_status"])
        self.assertEqual(1, by_slug["fanrank"]["featured_rank"])
        self.assertEqual(1, by_slug["fanrank"]["team_member_star_cap"])
        self.assertEqual("normal", by_slug["fanrank"]["topic_tier"])
        self.assertEqual(5, by_slug["fanrank"]["topic_limit"])
        self.assertEqual(0, by_slug["fanrank"]["topic_active_count"])
        self.assertEqual("es", by_slug["rubius"]["default_language"])
        self.assertEqual("es", by_slug["orslok"]["default_language"])
        self.assertEqual("es", by_slug["ibai"]["default_language"])
        self.assertEqual("auto", by_slug["discord"]["default_language"])
        self.assertEqual("auto", by_slug["chatgpt"]["default_language"])

        query = urllib.parse.urlencode(
            {
                "select": "id,section,title,ai_score,web_votes,team_interest_count,owner_pick,owner_star_value,team_star_support_count,topic_id,topic_title,topic_status",
                "section": "eq.brawl-stars",
            }
        )
        status, raw = api_request(f"fr_ranking?{query}")
        self.assertEqual(200, status, raw)
        ideas = json.loads(raw)
        self.assertGreaterEqual(len(ideas), 30)
        self.assertTrue(all(row["team_interest_count"] == 0 for row in ideas))
        self.assertTrue(all(row["owner_pick"] is False for row in ideas))
        self.assertTrue(all(row["owner_star_value"] == 0 for row in ideas))
        self.assertTrue(all(row["team_star_support_count"] == 0 for row in ideas))
        self.assertTrue(all(row["topic_id"] is None for row in ideas))

        status, raw = api_request("fr_profile_topics_public?select=id,section,title,description,status,sort_order")
        self.assertEqual(200, status, raw)
        self.assertEqual([], json.loads(raw))

        status, raw = api_request("fr_profile_topics?select=created_by")
        self.assertIn(status, (401, 403), raw)

    def test_private_queues_cannot_be_read_anonymously(self) -> None:
        for table in (
            "fr_submissions",
            "fr_claims",
            "fr_events",
            "fr_votes",
            "fr_profile_members",
            "fr_team_interests",
            "fr_profile_invites",
            "fr_platform_admins",
            "fr_owner_feedback",
            "fr_profile_requests",
            "fr_promotion_requests",
            "fr_pro_requests",
            "fr_submission_attachments",
            "fr_fan_profiles",
        ):
            with self.subTest(table=table):
                status, raw = api_request(f"{table}?select=*")
                self.assertIn(status, (401, 403), raw)

    def test_rls_rejects_invalid_public_writes(self) -> None:
        probes = [
            ("fr_submissions", {"section": "brawl-stars", "title": "x"}),
            ("fr_claims", {"section": "brawl-stars", "name": "x", "role": "x", "contact": "x"}),
            ("fr_votes", {"idea_id": 1, "voter": "short"}),
            (
                "fr_owner_feedback",
                {"user_id": "00000000-0000-0000-0000-000000000000", "page_path": "/", "zone": "hero", "message": "x"},
            ),
            (
                "fr_profile_requests",
                {"requested_by": "00000000-0000-0000-0000-000000000000", "name": "Test", "kind": "company"},
            ),
            (
                "fr_promotion_requests",
                {"user_id": "00000000-0000-0000-0000-000000000000", "section": "fanrank", "placement": "profile"},
            ),
            (
                "fr_pro_requests",
                {
                    "user_id": "00000000-0000-0000-0000-000000000000",
                    "organization_name": "Test",
                    "plan": "signal",
                    "feedback_band": "under_1000",
                    "cadence": "weekly",
                    "goal": "This direct write must be rejected",
                },
            ),
            (
                "fr_profile_topics",
                {
                    "section": "fanrank",
                    "title": "Anonymous topic",
                    "created_by": "00000000-0000-0000-0000-000000000000",
                    "updated_by": "00000000-0000-0000-0000-000000000000",
                },
            ),
        ]
        for table, body in probes:
            with self.subTest(table=table):
                status, raw = api_request(table, method="POST", body=body)
                self.assertIn(status, (401, 403), raw)
                self.assertEqual("42501", json.loads(raw)["code"])

        status, raw = api_request("fr_events", method="POST", body={"event": "not_an_allowed_event"})
        self.assertEqual(400, status, raw)
        self.assertEqual("23514", json.loads(raw)["code"])

    def test_anon_cannot_use_team_rpcs_but_receipt_lookup_is_non_enumerable(self) -> None:
        for rpc, body in (
            ("fr_set_team_interest", {"p_idea_id": 1, "p_active": True}),
            ("fr_my_team_interests", {"p_section": "brawl-stars"}),
            ("fr_set_team_star", {"p_idea_id": 1, "p_value": 1}),
            ("fr_my_team_stars", {"p_section": "brawl-stars"}),
            ("fr_set_team_star_cap", {"p_section": "fanrank", "p_cap": 3}),
            ("fr_team_submission_inbox", {"p_section": "fanrank", "p_limit": 1}),
            (
                "fr_upsert_profile_topic",
                {
                    "p_section": "fanrank",
                    "p_topic_id": None,
                    "p_title": "Anonymous topic",
                    "p_description": "Must be rejected",
                    "p_sort_order": 100,
                },
            ),
            ("fr_archive_profile_topic", {"p_section": "fanrank", "p_topic_id": 1}),
            ("fr_set_idea_topic", {"p_idea_id": 1, "p_topic_id": None}),
            (
                "fr_create_profile_invite",
                {"p_section": "brawl-stars", "p_email": "nobody@example.com", "p_role": "contributor"},
            ),
            ("fr_profile_team", {"p_section": "brawl-stars"}),
            (
                "fr_admin_set_profile_image",
                {
                    "p_section": "fanrank",
                    "p_path": "fanrank/nope/file.webp",
                    "p_alt": "Nope",
                    "p_source_url": None,
                    "p_credit": None,
                    "p_rights": "generated",
                },
            ),
            (
                "fr_request_pro_pilot",
                {
                    "p_section": "fanrank",
                    "p_organization": "Anonymous probe",
                    "p_plan": "signal",
                    "p_feedback_band": "under_1000",
                    "p_cadence": "weekly",
                    "p_goal": "This anonymous call must be rejected",
                },
            ),
            ("fr_my_fan_profile", {}),
            (
                "fr_upsert_my_fan_profile",
                {
                    "p_handle": "anonymous-probe",
                    "p_display_name": "Anonymous Probe",
                    "p_headline": "",
                    "p_skills": [],
                    "p_is_public": False,
                    "p_available_for_opportunities": False,
                },
            ),
            ("fr_set_submission_ai_consent", {"p_submission_id": 1, "p_consent": True}),
            (
                "fr_register_milestone_subscription",
                {
                    "p_receipt_hash": "0" * 64,
                    "p_email": "probe@example.invalid",
                    "p_milestones": ["hearts_100"],
                    "p_language": "es",
                },
            ),
        ):
            with self.subTest(rpc=rpc):
                status, raw = api_request(f"rpc/{rpc}", method="POST", body=body)
                self.assertIn(status, (401, 403), raw)

        status, raw = api_request(
            "rpc/fr_submission_status", method="POST", body={"p_receipt": "0" * 64}
        )
        self.assertEqual(200, status, raw)
        self.assertEqual([], json.loads(raw))

    def test_live_evidence_validator_requires_canonical_youtube_links(self) -> None:
        cases = [
            (["https://www.youtube.com/watch?v=dQw4w9WgXcQ"], True),
            (["https://example.com/supporting-proof"], True),
            (["https://youtu.be/dQw4w9WgXcQ"], False),
            (["https://youtube.com.evil.test/watch?v=dQw4w9WgXcQ"], False),
            (["https://www.youtube.com/watch?v=dQw4w9WgXcQ#fragment"], False),
            (["https://example.com/a", "https://example.com/a"], False),
        ]
        for links, expected in cases:
            with self.subTest(links=links):
                status, raw = api_request(
                    "rpc/fr_valid_evidence_links",
                    method="POST",
                    body={"p_links": links},
                )
                self.assertEqual(200, status, raw)
                self.assertIs(expected, json.loads(raw))

    def test_private_media_intake_requires_a_real_session(self) -> None:
        request = urllib.request.Request(
            f"{SB_URL}/functions/v1/fanrank-feedback-intake",
            data=b"--fanrank--\r\n",
            headers={
                "apikey": SB_KEY,
                "Origin": "https://eltonylfgi-blip.github.io",
                "Content-Type": "multipart/form-data; boundary=fanrank",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                status = response.status
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            status = error.code
            raw = error.read().decode("utf-8")
        self.assertIn(status, (401, 403), raw)

    def test_milestone_alert_intake_rejects_invalid_receipts_without_auth_or_writes(self) -> None:
        request = urllib.request.Request(
            f"{SB_URL}/functions/v1/fanrank-milestone-alerts",
            data=json.dumps(
                {
                    "receipt": "too-short",
                    "email": "probe@example.invalid",
                    "milestones": ["hearts_100"],
                    "language": "es",
                    "website": "",
                }
            ).encode("utf-8"),
            headers={
                "apikey": SB_KEY,
                "Origin": "https://eltonylfgi-blip.github.io",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                status = response.status
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            status = error.code
            raw = error.read().decode("utf-8")
        self.assertEqual(400, status, raw)
        self.assertIn("Recibo", raw)


class UnclaimedProfileSafetyTests(unittest.TestCase):
    """FR-INV-010 (P0 legal, Tony 17-jul-2026): el ACOPLE VA AL REVES.

    Un perfil no reclamado SI sale en Google -- Google es el unico canal que trae
    gente gratis-- pero SOLO si lleva puesto el aviso de no-afiliacion y la via de
    retirada. Estos tests fallan si alguien quita el aviso o la via de retirada, y
    si alguna pagina INDEXABLE se queda sin ellos.
    """

    # Personas y entidades REALES publicadas hoy sin haber reclamado su perfil.
    # Reclamar ya no cambia la indexabilidad: solo cambia el titular de la frase.
    REAL_UNCLAIMED = ("orslok", "ibai", "rubius", "brawl-stars")
    UNCLAIMED_MARK = "Perfil no reclamado"
    # La frase que hace indexable una pagina. Aparece TAMBIEN en la variante reclamada:
    # es la marca universal, no la de "no reclamado".
    NON_AFFILIATION_MARK = "no est&aacute; afiliado, patrocinado ni respaldado"
    NOINDEX_META = '<meta name="robots" content="noindex,follow">'
    REMOVAL_ISSUES_URL = "https://github.com/eltonylfgi-blip/fanrank/issues/new"
    EMAIL_LITERAL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)

    def _removal_path(self, raw: str) -> bool:
        return self.REMOVAL_ISSUES_URL in raw

    def test_app_profile_shows_a_visible_non_affiliation_notice(self) -> None:
        self.assertIn('id="claim-disclaimer"', HTML)
        self.assertIn('<span class="claim-disclaimer" id="claim-disclaimer">', HTML)
        self.assertIn(
            'claim_disclaimer:"FanRank no está afiliado, patrocinado ni respaldado por las '
            'personas y marcas que aparecen aquí.',
            HTML,
        )
        self.assertIn(
            'claim_disclaimer:"FanRank is not affiliated with, sponsored by or endorsed by '
            "the people and brands shown here.",
            HTML,
        )
        self.assertEqual(2, HTML.count("claim_disclaimer_named:"), "aviso en EN y ES")
        self.assertIn(
            'byId("claim-disclaimer").textContent = named ? tx("claim_disclaimer_named",named) '
            ': tx("claim_disclaimer");',
            HTML,
        )
        self.assertIn("  applyClaimNotice();", HTML)
        # Se lee: ni gris de 8px ni escondido en el footer.
        self.assertRegex(HTML, r"[.]profile-legal [.]claim-disclaimer\{[^}]*color:var\(--text\)")
        self.assertRegex(HTML, r"[.]profile-legal [.]claim-disclaimer\{[^}]*font-size:[.]84rem")

    def test_the_notice_does_not_live_inside_the_bar_that_gets_hidden(self) -> None:
        """La claim-bar se ESCONDE al reclamar. El aviso no puede ir dentro de ella:
        si no, reclamar volveria a apagar el aviso por la puerta de atras."""
        self.assertIn('<div class="profile-legal" id="profile-legal">', HTML)
        # El aviso y la retirada cuelgan de profile-legal, NO de claim-copy.
        self.assertRegex(
            HTML,
            r'<div class="profile-legal" id="profile-legal">'
            r'<span class="claim-disclaimer" id="claim-disclaimer"></span>'
            r'<a class="claim-remove" id="claim-remove"',
        )
        self.assertNotRegex(HTML, r'<div class="claim-copy">[^\n]*id="claim-disclaimer"')
        self.assertNotRegex(HTML, r'<div class="claim-copy">[^\n]*id="claim-remove"')
        # Lo que se esconde al reclamar es la BARRA, nunca el aviso.
        self.assertIn(
            'document.querySelector(".claim-bar").classList.toggle("hidden",'
            "isClaimedProfile(secMeta));",
            HTML,
        )

    def test_app_profile_offers_a_real_prefilled_removal_path(self) -> None:
        self.assertIn('<a class="claim-remove" id="claim-remove"', HTML)
        self.assertIn(f'var REMOVAL_ISSUES_URL = "{self.REMOVAL_ISSUES_URL}";', HTML)
        self.assertIn('destination.searchParams.set("title",tx("claim_remove_subject",name))', HTML)
        self.assertIn('destination.searchParams.set("body",tx("claim_remove_body",name,url))', HTML)
        self.assertEqual(2, HTML.count("claim_remove_link:"), "enlace en EN y ES")
        self.assertEqual(2, HTML.count("claim_remove_subject:"))
        self.assertEqual(2, HTML.count("claim_remove_body:"))
        self.assertIn('claim_remove_link:"¿Eres tú o su representante? Pide que lo quitemos"', HTML)
        self.assertIn(
            'claim_remove_link:"Are you them or their representative? Ask us to remove it"', HTML
        )
        self.assertRegex(HTML, r"[.]claim-remove\{[^}]*min-height:44px")

    def test_removal_link_builds_a_prefilled_public_request_without_personal_email(self) -> None:
        """La via abre una solicitud escrita sin publicar una direccion personal."""
        functions = "\n".join(
            extract_js_function(name)
            for name in (
                "normalizeLanguage", "persistentUrl", "profileDefaultLanguage",
                "setUrlLanguage", "profileStubUrl", "profileRemovalUrl",
            )
        )
        node_program = "\n".join([
            'var TELEMETRY_DISABLED=false;',
            'var LANG="es";',
            'var URL_LANGUAGE="es";',
            'var SAVED_LANGUAGE=null;',
            'var APP_URL="https://eltonylfgi-blip.github.io/fanrank/";',
            f'var REMOVAL_ISSUES_URL="{self.REMOVAL_ISSUES_URL}";',
            'var sections=[{slug:"orslok",default_language:"es"}];',
            'var location={origin:"https://eltonylfgi-blip.github.io",pathname:"/fanrank/",'
            'search:"?s=orslok",href:"https://eltonylfgi-blip.github.io/fanrank/?s=orslok"};',
            'var T={es:{claim_remove_subject:function(n){return "FanRank - retirad el perfil de " + n;},'
            'claim_remove_body:function(n,u){return "Soy " + n + ". Perfil: " + u;}}};',
            'function tx(key){var v=T[LANG][key];'
            'return typeof v === "function" ? v.apply(null,Array.prototype.slice.call(arguments,1)) : v;}',
            functions,
            'console.log(profileRemovalUrl("Orslok","orslok"));',
        ])
        result = subprocess.run(
            ["node", "-e", node_program], cwd=ROOT, capture_output=True,
            text=True, encoding="utf-8", check=False, timeout=10,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        removal = result.stdout.strip()
        parsed = urllib.parse.urlsplit(removal)
        self.assertEqual(("https", "github.com", "/eltonylfgi-blip/fanrank/issues/new"),
                         (parsed.scheme, parsed.netloc, parsed.path))
        query = urllib.parse.parse_qs(parsed.query)
        self.assertIn("Orslok", query["title"][0])
        self.assertIn("Orslok", query["body"][0])
        self.assertIsNone(self.EMAIL_LITERAL.search(removal))
        # El cuerpo lleva el PERFIL concreto: quien lo recibe sabe que retirar.
        self.assertIn("https://eltonylfgi-blip.github.io/fanrank/p/orslok/", query["body"][0])

    def test_app_indexability_hangs_on_the_notice_not_on_the_claim(self) -> None:
        """EL ACOPLE INVERTIDO en la app: el robots es CONSECUENCIA del aviso pintado."""
        self.assertIn("function setRobotsNoindex(noindex)", HTML)
        self.assertIn(
            'meta.setAttribute("content",noindex ? "noindex,follow" : ROBOTS_INDEXABLE);', HTML
        )
        self.assertIn("function profileDisclosureOk()", HTML)
        self.assertIn("setRobotsNoindex(!profileDisclosureOk());", HTML)
        # Reclamar YA NO decide si sales en Google (Tony 17-jul: "mejor q salgamos en google").
        self.assertNotIn("setRobotsNoindex(!isClaimedProfile(secMeta));", HTML)
        self.assertIn('return !!(meta && meta.verification_status === "verified");', HTML)
        # La puerta mira el aviso REAL: visible, con texto y con el destino exacto.
        self.assertIn('var note = byId("claim-disclaimer");', HTML)
        self.assertIn('var link = byId("claim-remove");', HTML)
        self.assertIn('removalUrl.pathname === "/eltonylfgi-blip/fanrank/issues/new"', HTML)
        self.assertIn('return !!(node && !node.closest(".hidden"));', HTML)
        # El aviso se pinta ANTES de decidir el robots (si no, mediria el DOM vacio).
        self.assertRegex(
            HTML,
            r"applyClaimNotice\(\);\n(?:\s*//[^\n]*\n)*\s*setRobotsNoindex\(!profileDisclosureOk\(\)\);",
        )
        # Se VOLTEA el meta que ya existe. Dos metas robots en conflicto solo
        # funcionan porque Google aplica la mas restrictiva: no dependemos de eso.
        self.assertEqual(1, HTML.count('<meta name="robots"'), "un solo meta robots estatico")
        self.assertIn('document.head.querySelector(\'meta[name="robots"]\')', HTML)
        self.assertNotIn('meta.id = "robots-meta"', HTML)

    def test_third_party_ip_notice_is_wired_for_supercell_games(self) -> None:
        self.assertIn('id="ip-notice"', HTML)
        self.assertIn('"brawl-stars":"supercell"', HTML)
        self.assertIn(
            'IP_NOTICE_URLS = {supercell:"https://supercell.com/en/fan-content-policy/"};', HTML
        )
        self.assertIn(
            'ip_notice_supercell:"This material is unofficial and is not endorsed by Supercell.',
            HTML,
        )
        self.assertIn(
            'ip_notice_supercell:"Este material no es oficial y no está respaldado por Supercell.',
            HTML,
        )
        self.assertIn("function applyIpNotice()", HTML)

    def test_profile_stub_generator_hangs_indexability_on_the_notice(self) -> None:
        generator = PROFILE_STUB_GENERATOR.read_text(encoding="utf-8")
        for marker in (
            "fr_sections_stats?select=slug,name,default_language,verification_status",
            "def is_claimed(profile: dict) -> bool:",
            'return str(profile.get("verification_status") or "") == "verified"',
            f'REMOVAL_ISSUES_URL = "{self.REMOVAL_ISSUES_URL}"',
            "def removal_issue_url(raw_name: str, slug: str) -> str:",
            "def legal_block(profile: dict) -> str:",
            "def page_is_indexable(legal: str) -> bool:",
            "return NON_AFFILIATION_MARK in legal and REMOVAL_MARK in legal",
            'NOINDEX_META = \'\\n  <meta name="robots" content="noindex,follow">\'',
            "robots_meta = \"\" if page_is_indexable(legal_html) else NOINDEX_META",
            '"brawl-stars": "supercell"',
        ):
            self.assertIn(marker, generator)
        # El robots NO puede volver a colgar del flag de reclamado.
        self.assertNotIn('robots_meta = "" if claimed else', generator)
        result = subprocess.run(
            [sys.executable, str(PROFILE_STUB_GENERATOR), "--selftest"],
            cwd=ROOT, capture_output=True, text=True, check=False, timeout=30,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        self.assertIn("SELFTEST: OK", result.stdout)

    def test_top_page_generator_hangs_indexability_on_the_notice(self) -> None:
        generator = TOP_PAGES_GENERATOR.read_text(encoding="utf-8")
        for marker in (
            "fr_sections_stats?select=slug,name,default_language,verification_status",
            "def is_claimed(section):",
            f'REMOVAL_ISSUES_URL = "{self.REMOVAL_ISSUES_URL}"',
            "def removal_issue_url(name, slug):",
            "def legal_block(section):",
            "def page_is_indexable(legal):",
            "return NON_AFFILIATION_MARK in legal and REMOVAL_MARK in legal",
            'robots = "" if page_is_indexable(legal) else NOINDEX_META',
            "if page_is_indexable(legal_block(section)):",
            '"brawl-stars": "supercell"',
        ):
            self.assertIn(marker, generator)
        self.assertNotIn('robots = "" if claimed else', generator)
        self.assertNotIn("if is_claimed(section):\n            urls.append", generator)
        result = subprocess.run(
            [sys.executable, str(TOP_PAGES_GENERATOR), "--selftest"],
            cwd=ROOT, capture_output=True, text=True, check=False, timeout=30,
        )
        self.assertEqual(0, result.returncode, result.stderr or result.stdout)
        self.assertIn("SELFTEST: OK", result.stdout)

    def _published_profile_pages(self) -> list[Path]:
        return sorted(PROFILE_STUB_ROOT.glob("*/index.html")) + sorted(TOP_ROOT.glob("*/index.html"))

    def test_no_indexable_page_can_ever_lack_the_notice(self) -> None:
        """EL CANDADO (Tony 17-jul): si una pagina puede ir a Google, LLEVA aviso.

        Es el test que caza al que manana anada un perfil nuevo y se olvide del aviso:
        no le exige acordarse de poner noindex, le exige el AVISO para poder indexar.
        """
        pages = self._published_profile_pages()
        self.assertGreaterEqual(len(pages), 10)
        indexables = 0
        for page in pages:
            with self.subTest(page=str(page.relative_to(ROOT))):
                raw = page.read_text(encoding="utf-8")
                if self.NOINDEX_META in raw:
                    continue  # fuera de Google: el aviso es indiferente
                indexables += 1
                self.assertIn(
                    self.NON_AFFILIATION_MARK, raw,
                    "pagina INDEXABLE sin aviso de no-afiliacion: prohibido",
                )
                self.assertTrue(
                    self._removal_path(raw),
                    "pagina INDEXABLE sin via de retirada de 1 tap: prohibido",
                )
        # Y que el test no pase por vacio: tiene que haber paginas indexables de verdad.
        self.assertGreaterEqual(indexables, 10, "nadie volvio a Google: revisa el noindex")

    def test_every_real_unclaimed_profile_page_is_back_on_google_with_its_notice(self) -> None:
        for slug in self.REAL_UNCLAIMED:
            for root in (PROFILE_STUB_ROOT, TOP_ROOT):
                page = root / slug / "index.html"
                if not page.exists():
                    continue
                with self.subTest(page=str(page.relative_to(ROOT))):
                    raw = page.read_text(encoding="utf-8")
                    # Vuelve a Google...
                    self.assertNotIn(self.NOINDEX_META, raw)
                    # ...pero jamas sin el aviso ni la via de retirada.
                    self.assertIn(self.UNCLAIMED_MARK, raw)
                    self.assertIn(self.NON_AFFILIATION_MARK, raw)
                    self.assertIn("Pide que lo quitemos", raw)
                    self.assertIn(self.REMOVAL_ISSUES_URL, raw)

    def test_public_html_never_embeds_a_personal_email_address(self) -> None:
        pages = [INDEX, *self._published_profile_pages()]
        for page in pages:
            with self.subTest(page=str(page.relative_to(ROOT))):
                raw = page.read_text(encoding="utf-8")
                self.assertIsNone(
                    self.EMAIL_LITERAL.search(raw),
                    "una pagina publica incrusta una direccion personal",
                )

    def test_supercell_pages_carry_the_fan_content_notice(self) -> None:
        for root in (PROFILE_STUB_ROOT, TOP_ROOT):
            page = root / "brawl-stars" / "index.html"
            if not page.exists():
                continue
            with self.subTest(page=str(page.relative_to(ROOT))):
                raw = page.read_text(encoding="utf-8")
                self.assertIn("no est&aacute; respaldado por Supercell", raw)
                self.assertIn("supercell.com/en/fan-content-policy", raw)

    def test_sitemaps_only_advertise_pages_that_carry_the_notice(self) -> None:
        """Anunciar a Google == poder ir a Google == llevar el aviso. Misma puerta."""
        top_raw = (TOP_ROOT / "sitemap-top.xml").read_text(encoding="utf-8")
        for slug in re.findall(r"/top/([a-z0-9-]+)/</loc>", top_raw):
            with self.subTest(sitemap="sitemap-top.xml", slug=slug):
                raw = (TOP_ROOT / slug / "index.html").read_text(encoding="utf-8")
                self.assertNotIn(self.NOINDEX_META, raw)
                self.assertIn(self.NON_AFFILIATION_MARK, raw)
                self.assertTrue(self._removal_path(raw))
        root_raw = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        for slug in re.findall(r"\?s=([a-z0-9-]+)</loc>", root_raw):
            with self.subTest(sitemap="sitemap.xml", slug=slug):
                stub = PROFILE_STUB_ROOT / slug / "index.html"
                self.assertTrue(stub.exists(), f"sitemap anuncia {slug} sin stub publicado")
                raw = stub.read_text(encoding="utf-8")
                self.assertNotIn(self.NOINDEX_META, raw)
                self.assertIn(self.NON_AFFILIATION_MARK, raw)
                self.assertTrue(self._removal_path(raw))

    def test_the_profiles_are_advertised_to_google_again(self) -> None:
        """Tony 17-jul: "mejor q salgamso en google". Si no estan en el sitemap, no salen."""
        root_raw = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
        for slug in self.REAL_UNCLAIMED:
            with self.subTest(sitemap="sitemap.xml", slug=slug):
                self.assertIn(f"?s={slug}</loc>", root_raw)
        top_raw = (TOP_ROOT / "sitemap-top.xml").read_text(encoding="utf-8")
        for slug in sorted(p.name for p in TOP_ROOT.iterdir() if p.is_dir()):
            with self.subTest(sitemap="sitemap-top.xml", slug=slug):
                self.assertIn(f"/top/{slug}/</loc>", top_raw)


class ZeroSupportTests(unittest.TestCase):
    """Matar el cero: 0 corazones NO se gritan (un tablon de ceros parece muerto),
    pero jamas se inventan votos ni se infla nada (FR-INV-005)."""

    def test_an_idea_without_support_asks_for_the_first_one(self) -> None:
        self.assertIn("function needsFirstVote(item)", HTML)
        self.assertIn("return Number(item && item.web_votes || 0) === 0;", HTML)
        self.assertEqual(2, HTML.count("be_first:"), "CTA en EN y ES")
        self.assertEqual(2, HTML.count("be_first_long:"), "CTA en EN y ES")
        self.assertIn('be_first_long:"Sé el primero en apoyarla"', HTML)
        self.assertIn('be_first_long:"Be the first to back it"', HTML)

    def test_the_zero_is_never_painted(self) -> None:
        # Ficha de idea: con 0 corazones no se pinta el contador.
        self.assertIn(
            '(firstVote ? "" : \'<span class="vote-count">\' + Number(item.web_votes||0) + \'</span>\')',
            HTML,
        )
        self.assertIn('esc(voted ? tx("voted") : firstVote ? tx("be_first") : tx("vote"))', HTML)
        # Chip de origen: sin apoyo en la fuente no hay chip que diga "0".
        self.assertIn('(Number(item.origin_upvotes||0) > 0 ? \'<span class="chip"', HTML)
        # Home e ideas similares.
        self.assertIn('? (needsFirstVote(item) ? tx("be_first_long") : tx("global_fan_signal"', HTML)
        self.assertIn(
            'esc(needsFirstVote(item) ? tx("be_first_long") : Number(item.web_votes || 0) + " " + tx("similar_votes"))',
            HTML,
        )

    def test_killing_the_zero_never_invents_support(self) -> None:
        body = extract_js_function("needsFirstVote")
        for forbidden in ("Math.random", "Math.max", "+ 1", "|| 1"):
            self.assertNotIn(forbidden, body)
        # El ranking sigue leyendo el numero REAL, no el CTA.
        self.assertIn("Math.min(Number(item.web_votes || 0) * 2,20)", extract_js_function("rankScore"))
        for name in ("rankScore", "sortedIdeas"):
            self.assertNotIn("needsFirstVote", extract_js_function(name))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="also check the live Supabase boundary")
    args, remaining = parser.parse_known_args()
    selected = [
        StaticAppTests,
        V18UsabilityTests,
        V19EngagementTests,
        UnclaimedProfileSafetyTests,
        ZeroSupportTests,
    ]
    if args.live:
        selected.append(LiveBoundaryTests)
    suite = unittest.TestSuite()
    loader = unittest.defaultTestLoader
    for case in selected:
        suite.addTests(loader.loadTestsFromTestCase(case))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

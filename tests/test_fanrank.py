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
SOCIAL_CARD = ROOT / "social-card.png"
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
MEDIA_INTAKE_PATH = ROOT / "supabase" / "functions" / "fanrank-feedback-intake" / "index.ts"
MEDIA_INTAKE = MEDIA_INTAKE_PATH.read_text(encoding="utf-8")


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
    def test_utf8_and_mobile_document(self) -> None:
        self.assertIn('<meta charset="UTF-8">', HTML)
        self.assertIn('name="viewport"', HTML)
        self.assertIn("FanRank — the best ideas, ranked", HTML)
        self.assertNotIn("â€”", HTML)

        suggest_dialog = extract(r'<dialog id="suggest-dialog"[\s\S]*?<form id="submit-form"[^>]*>([\s\S]*?)</form>')
        self.assertEqual(1, suggest_dialog.count("<textarea"))
        self.assertIn('<input id="submit-details" type="hidden">', suggest_dialog)
        self.assertLess(
            suggest_dialog.index('<section class="privacy-box"'),
            suggest_dialog.index('id="submit-send"'),
            "Identity and private contact choices must stay next to the idea and before the single send action.",
        )
        self.assertIn('class="submit-bar"', suggest_dialog)
        self.assertIn("margin:18px 0 0", HTML)
        self.assertIn("margin:16px 0 0", HTML)
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
            "owner studio bundle": 'owner-studio.js?v=8',
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
        self.assertIn('autocomplete="current-password"', HTML)
        self.assertIn("authClient.auth.updateUser({password:nextPassword})", HTML)
        self.assertIn('autocomplete="new-password"', HTML)
        self.assertIn("if(REDUCED || !audioArmed || !audioContext || chimePlayed)", HTML)
        self.assertIn("setTimeout(function(){chimePlayed = false;},9000)", HTML)
        self.assertIn("brand-mark-heart", HTML)
        self.assertIn("brand-mark-team", HTML)
        self.assertIn('secMeta.verification_status === "verified"', HTML)
        self.assertIn('document.body.classList.toggle("team-mode",teamMode)', HTML)
        self.assertIn("M50 6 61.8 36.2 94.5 38.1", HTML)

    def test_private_media_fan_profiles_and_consent_are_wired_end_to_end(self) -> None:
        html_markers = [
            'accept="image/png,image/jpeg,image/webp"',
            'byId("suggest-dialog").addEventListener("paste"',
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
            'id="submit-target-context"',
            'tx("submit_for",secMeta.name)',
            '<label class="field-label" id="evidence-link-label" for="evidence-link-input">',
            'byId("evidence-link-label").textContent = tx("evidence_link_label")',
            'byId("logo").setAttribute("aria-label",tx(teamMode ? "logo_team_label" : "logo_public_label"))',
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])
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
            "persistentUrl",
            "homeUrl",
            "fanProfileUrl",
            "fanSuggestionUrl",
            "teamInviteUrl",
            "sectionUrl",
            "ideaUrl",
        )
        functions = "\n".join(extract_js_function(name) for name in function_names)
        node_program = "\n".join(
            [
                'var TELEMETRY_DISABLED=true;',
                'var LANG="es";',
                'var SECTION="orslok";',
                (
                    'var location={origin:"https://eltonylfgi-blip.github.io",pathname:"/fanrank/",'
                    'search:"?s=orslok&lang=es&qa=1",'
                    'href:"https://eltonylfgi-blip.github.io/fanrank/?s=orslok&lang=es&qa=1"};'
                ),
                functions,
                (
                    'console.log(JSON.stringify({'
                    'home:homeUrl(),section:sectionUrl("orslok",true),'
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
        self.assertEqual(["17"], urllib.parse.parse_qs(parsed["idea"].query).get("idea"))
        self.assertEqual(["tony"], urllib.parse.parse_qs(parsed["fan"].query).get("fan"))
        self.assertEqual(["17"], urllib.parse.parse_qs(parsed["fanIdea"].query).get("idea"))
        self.assertEqual("invite=invite-token", parsed["invite"].fragment)

    def test_mobile_suggestion_cta_never_competes_with_inline_cta(self) -> None:
        markers = [
            "body.profile-live.mobile-cta-ready .mobile-suggest",
            "body.home-live.mobile-cta-ready .mobile-suggest",
            "body.suggest-dialog-open .mobile-suggest",
            "new IntersectionObserver",
            'document.body.classList.toggle("mobile-cta-ready",!entries[0].isIntersecting)',
            'document.body.classList.add("suggest-dialog-open")',
            'document.body.classList.remove("suggest-dialog-open")',
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])

    def test_every_emitted_event_is_allowed_and_qa_is_excluded(self) -> None:
        emitted = set(re.findall(r'sendEvent\("([a-z0-9_]+)"', HTML + "\n" + OWNER_JS))
        blocks = re.findall(
            r"add constraint fr_events_event_check\s+check \(event in \((.*?)\)\);",
            EVIDENCE_SQL,
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
        ]
        self.assertEqual([], [marker for marker in markers if marker not in OWNER_JS])
        self.assertIn("body.fr-zone-picking [data-feedback-zone]", OWNER_CSS)
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
        self.assertIn(
            'document.querySelector(".claim-bar").classList.toggle("hidden",secMeta.verification_status === "verified")',
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
            'id="fan-value-title"',
            'id="home-profile-cta"',
            'id="directory-more"',
            'var initialLimit = window.matchMedia("(max-width:560px)").matches ? 3 : 6;',
            'var familiar = ["rubius","brawl-stars","discord"',
            "scroll-snap-type:x mandatory",
            '.trend-card{flex:0 0 min(360px,82%)',
            "rank-r",
            "rank-a",
            "rank-k",
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
        self.assertRegex(HTML, r"[.]logo-art\{[^}]*max-width:calc\(100vw - 32px\)")
        self.assertRegex(HTML, r"[.]rank-trophy\{[^}]*width:[.]74em;height:[.]74em")
        self.assertLess(HTML.index('id="home-suggest"'), HTML.index('id="directory-filters"'))

        sorted_ideas = extract(r"function sortedIdeas\(source\)\{([\s\S]*?)\n\}")
        self.assertIn('return rankScore(b)-rankScore(a)', sorted_ideas)
        self.assertIn('return Number(b.ai_score)-Number(a.ai_score)', sorted_ideas)
        self.assertIn('return Number(b.web_votes)-Number(a.web_votes)', sorted_ideas)

    def test_celestial_logo_respects_user_control(self) -> None:
        markers = [
            "logoShine",
            "starBloom",
            "document.addEventListener(\"pointerdown\",armCelestialAudio",
            "byId(\"logo\").addEventListener(\"pointerenter\"",
            "if(REDUCED || !audioArmed",
            "chimePlayed",
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])

    def test_profile_sharing_has_a_clean_measurable_referral_loop(self) -> None:
        markers = [
            '<link rel="canonical" href="https://eltonylfgi-blip.github.io/fanrank/">',
            '<meta property="og:title"',
            '<meta property="og:image" content="https://eltonylfgi-blip.github.io/fanrank/social-card.png">',
            '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="630">',
            '<meta name="twitter:card" content="summary_large_image">',
            '<meta name="twitter:image" content="https://eltonylfgi-blip.github.io/fanrank/social-card.png">',
            'id="profile-share"',
            'id="profile-share-text"',
            "function referralSource()",
            "var REFERRAL_SOURCES = {fan_share:true,idea_share:true,reddit:true,discord:true,x:true,whatsapp:true};",
            "function withReferral(url,source)",
            "function profileShareUrl()",
            'withReferral(ideaUrl(item),"idea_share")',
            'sendEvent("idea_share",{section:SECTION,value:"profile"})',
            'sendEvent("page_view",{section:SECTION || null,value:referralSource()})',
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])
        self.assertIn("return REFERRAL_SOURCES[source] ? source : null;", HTML)

        card = SOCIAL_CARD.read_bytes()
        self.assertEqual(b"\x89PNG\r\n\x1a\n", card[:8])
        self.assertEqual((1200, 630), struct.unpack(">II", card[16:24]))
        self.assertGreater(len(card), 50_000)


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


class LiveBoundaryTests(unittest.TestCase):
    def test_public_directory_and_rankings_are_readable(self) -> None:
        status, raw = api_request(
            "fr_sections_stats?select=slug,name,kind,tags,featured_rank,ideas,recent_ideas,fan_votes,verification_status,team_member_star_cap"
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

        query = urllib.parse.urlencode(
            {
                "select": "id,section,title,ai_score,web_votes,team_interest_count,owner_pick,owner_star_value,team_star_support_count",
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="also check the live Supabase boundary")
    args, remaining = parser.parse_known_args()
    selected = [StaticAppTests]
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

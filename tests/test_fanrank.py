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
DISCOVERY_MIGRATION = ROOT / "supabase" / "migrations" / "20260715152000_fanrank_v6_discovery_directory.sql"
DISCOVERY_SQL = DISCOVERY_MIGRATION.read_text(encoding="utf-8")


def extract(pattern: str) -> str:
    match = re.search(pattern, HTML, re.DOTALL)
    if not match:
        raise AssertionError(f"Pattern not found: {pattern}")
    return match.group(1)


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
            "passwordless account": 'id="auth-form"',
            "private activity": 'id="activity-dialog"',
            "profile claim": 'id="claim-form"',
            "verified team management": 'id="team-dialog"',
            "secure invitation acceptance": 'id="invite-dialog"',
            "fan vote": 'data-vote="',
            "team heart": 'data-interest="',
            "shareable idea": "navigator.share",
            "product telemetry": 'postRow("fr_claims"',
            "event sink": 'fr_events',
            "bilingual UI": "var T = {",
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
            "receipt_hash:await hashReceipt",
            "allow_contact",
            'url.hash = "invite="',
            "function armCelestialAudio",
            "function playCelestialChime",
            "logoShakeSmooth",
            "tagPop",
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])
        self.assertNotIn("Search any <b>game, creator or company</b>", HTML)
        self.assertNotIn("Verified team picks score 100", HTML)
        self.assertNotIn("puntúan 100", HTML)

    def test_discovery_directory_is_practical_and_data_driven(self) -> None:
        html_markers = [
            '["featured","✦","Destacados"]',
            '["creators-es","🎙️","Creadores · España"]',
            '["games","🎮","Videojuegos"]',
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

    def test_auth_redirect_and_logo_effect_have_safe_guards(self) -> None:
        self.assertIn('options:{emailRedirectTo:authRedirectUrl(),shouldCreateUser:true}', HTML)
        self.assertIn('location.hostname === "localhost"', HTML)
        self.assertIn("if(REDUCED || !audioArmed || !audioContext || chimePlayed)", HTML)
        self.assertIn("setTimeout(function(){chimePlayed = false;},9000)", HTML)

    def test_team_signal_is_limited_and_not_a_public_identity_leak(self) -> None:
        self.assertIn("Math.min(Number(item.team_interest_count || 0) * 5,15)", HTML)
        self.assertIn("var av = rankScore(a);", HTML)
        self.assertIn("myTeamInterestIds.has(item.id)", HTML)
        self.assertIn("team_interest_count", HTML)
        self.assertIn("fr_set_team_interest", HTML)
        self.assertNotIn("owner_pick", HTML)
        self.assertNotIn("* 1000", HTML)

    def test_anonymous_submission_contract_matches_the_private_queue(self) -> None:
        self.assertIn('postRow("fr_submissions",{', HTML)
        self.assertIn("section:SECTION,title:title,", HTML)
        self.assertIn('headers:{"Prefer":"return=minimal"}', HTML)
        self.assertNotIn("section_slug:SECTION", HTML)

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
            '<meta property="og:title"',
            '<meta name="twitter:card" content="summary">',
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
            "fr_sections_stats?select=slug,name,kind,tags,featured_rank,ideas,recent_ideas,fan_votes,verification_status"
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

        query = urllib.parse.urlencode(
            {
                "select": "id,section,title,ai_score,web_votes,team_interest_count,owner_pick",
                "section": "eq.brawl-stars",
            }
        )
        status, raw = api_request(f"fr_ranking?{query}")
        self.assertEqual(200, status, raw)
        ideas = json.loads(raw)
        self.assertGreaterEqual(len(ideas), 30)
        self.assertTrue(all(row["team_interest_count"] == 0 for row in ideas))
        self.assertTrue(all(row["owner_pick"] is False for row in ideas))

    def test_private_queues_cannot_be_read_anonymously(self) -> None:
        for table in (
            "fr_submissions",
            "fr_claims",
            "fr_events",
            "fr_votes",
            "fr_profile_members",
            "fr_team_interests",
            "fr_profile_invites",
        ):
            with self.subTest(table=table):
                status, raw = api_request(f"{table}?select=*")
                self.assertIn(status, (401, 403), raw)

    def test_rls_rejects_invalid_public_writes(self) -> None:
        probes = [
            ("fr_submissions", {"section": "brawl-stars", "title": "x"}),
            ("fr_claims", {"section": "brawl-stars", "name": "x", "role": "x", "contact": "x"}),
            ("fr_votes", {"idea_id": 1, "voter": "short"}),
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
            (
                "fr_create_profile_invite",
                {"p_section": "brawl-stars", "p_email": "nobody@example.com", "p_role": "contributor"},
            ),
            ("fr_profile_team", {"p_section": "brawl-stars"}),
        ):
            with self.subTest(rpc=rpc):
                status, raw = api_request(f"rpc/{rpc}", method="POST", body=body)
                self.assertIn(status, (401, 403), raw)

        status, raw = api_request(
            "rpc/fr_submission_status", method="POST", body={"p_receipt": "0" * 64}
        )
        self.assertEqual(200, status, raw)
        self.assertEqual([], json.loads(raw))


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

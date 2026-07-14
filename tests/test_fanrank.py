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


def extract(pattern: str) -> str:
    match = re.search(pattern, HTML, re.DOTALL)
    if not match:
        raise AssertionError(f"Pattern not found: {pattern}")
    return match.group(1)


SB_URL = extract(r'var SB_URL = "([^"]+)";')
SB_KEY = extract(r'var SB_KEY = "([^"]+)";')


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
            "profile request": 'id="request-form"',
            "idea submission": 'id="submit-form"',
            "private contact": 'id="submit-contact"',
            "profile claim": 'id="claim-form"',
            "fan vote": 'data-vote="',
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
        pieces = SB_KEY.split(".")
        self.assertEqual(3, len(pieces))
        padded = pieces[1] + "=" * (-len(pieces[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        self.assertEqual("supabase", payload["iss"])
        self.assertEqual("kopegamcjozrvmxruwdn", payload["ref"])
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
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])

    def test_launch_copy_and_spam_guards_match_product_reality(self) -> None:
        markers = [
            "Starting with <b>Brawl Stars</b>",
            "UNVERIFIED FAN PROFILE",
            "PERFIL DE FANS NO VERIFICADO",
            'validTiming("submit-website","fr_last_submission",30000)',
            'validTiming("claim-website","fr_last_claim",60000)',
            'location.hostname === "127.0.0.1"',
        ]
        self.assertEqual([], [marker for marker in markers if marker not in HTML])
        self.assertNotIn("Search any <b>game, creator or company</b>", HTML)


def api_request(path: str, method: str = "GET", body: dict | None = None) -> tuple[int, str]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "apikey": SB_KEY,
        "Authorization": f"Bearer {SB_KEY}",
        "Content-Type": "application/json",
    }
    if method == "POST":
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
        status, raw = api_request("fr_sections_stats?select=slug,name,ideas,fan_votes")
        self.assertEqual(200, status, raw)
        sections = json.loads(raw)
        self.assertTrue(any(row["slug"] == "brawl-stars" for row in sections))

        query = urllib.parse.urlencode(
            {"select": "id,section,title,ai_score,web_votes", "section": "eq.brawl-stars"}
        )
        status, raw = api_request(f"fr_ranking?{query}")
        self.assertEqual(200, status, raw)
        ideas = json.loads(raw)
        self.assertGreaterEqual(len(ideas), 30)

    def test_private_queues_cannot_be_read_anonymously(self) -> None:
        for table in ("fr_submissions", "fr_claims", "fr_events"):
            with self.subTest(table=table):
                status, raw = api_request(f"{table}?select=*")
                self.assertIn(status, (401, 403), raw)

    def test_rls_rejects_invalid_public_writes(self) -> None:
        probes = [
            ("fr_submissions", {"section": "brawl-stars", "title": "x"}),
            ("fr_claims", {"section": "brawl-stars", "name": "x", "role": "x", "contact": "x"}),
            ("fr_events", {"event": "not_an_allowed_event"}),
        ]
        for table, body in probes:
            with self.subTest(table=table):
                status, raw = api_request(table, method="POST", body=body)
                self.assertEqual(401, status, raw)
                self.assertEqual("42501", json.loads(raw)["code"])


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

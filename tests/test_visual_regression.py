"""Browser-level guards for FanRank's logo and first profile viewport.

Run locally:
    python tests/test_visual_regression.py

The suite serves the checked-out app on an ephemeral localhost port and uses
the installed Microsoft Edge. It does not write data or call authenticated
product paths; ``qa=1`` disables telemetry.
"""

from __future__ import annotations

import functools
import http.server
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EDGE_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return


class FanRankVisualRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as error:
            raise unittest.SkipTest("Playwright is not installed") from error

        edge = next((path for path in EDGE_CANDIDATES if path.exists()), None)
        if edge is None:
            raise unittest.SkipTest("Microsoft Edge is not installed")

        handler = functools.partial(QuietHandler, directory=str(ROOT))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}/"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=str(edge),
            headless=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "browser"):
            cls.browser.close()
        if hasattr(cls, "playwright"):
            cls.playwright.stop()
        if hasattr(cls, "server"):
            cls.server.shutdown()
            cls.server.server_close()
        if hasattr(cls, "thread"):
            cls.thread.join(timeout=2)

    def test_logo_is_continuous_visible_and_inside_the_viewport(self) -> None:
        for width, height in ((375, 812), (768, 900), (1440, 1000)):
            with self.subTest(viewport=f"{width}x{height}"):
                context = self.browser.new_context(
                    viewport={"width": width, "height": height},
                    locale="es-ES",
                )
                page = context.new_page()
                page_errors: list[str] = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.goto(
                    self.base_url + "?lang=es&qa=1&local=logo-regression",
                    wait_until="domcontentloaded",
                )
                page.locator("[data-fanrank-logo]").wait_for(state="visible")
                geometry = page.evaluate(
                    """
                    () => {
                      const box = selector => document.querySelector(selector).getBoundingClientRect();
                      const art = box('.logo-art');
                      const rank = box('.rank-text');
                      const podium = box('.rank-podium');
                      const trophy = box('.rank-trophy');
                      const heart = box('.brand-mark');
                      const podiumSteps = [...document.querySelectorAll('.podium-step')].map(step => {
                        const stepBox = step.getBoundingClientRect();
                        const range = document.createRange();
                        range.selectNodeContents(step);
                        const textBox = range.getBoundingClientRect();
                        return {
                          height: stepBox.height,
                          textInside: textBox.top >= stepBox.top - 1 && textBox.bottom <= stepBox.bottom + 1
                        };
                      });
                      return {
                        viewport: innerWidth,
                        scrollWidth: document.documentElement.scrollWidth,
                        logoLeft: art.left,
                        logoRight: art.right,
                        rankText: document.querySelector('.rank-text').textContent.trim(),
                        rankRects: document.querySelector('.rank-text').getClientRects().length,
                        rankBottom: rank.bottom,
                        podiumTop: podium.top,
                        trophyWidth: trophy.width,
                        rankHeight: rank.height,
                        podiumSteps,
                        heartInside: heart.left >= art.left - 2 && heart.right <= art.right + 2,
                        trophyInside: trophy.left >= art.left - 2 && trophy.right <= art.right + 2
                      };
                    }
                    """
                )
                self.assertEqual([], page_errors)
                self.assertLessEqual(geometry["scrollWidth"], geometry["viewport"])
                self.assertGreaterEqual(geometry["logoLeft"], 8)
                self.assertLessEqual(geometry["logoRight"], geometry["viewport"] - 8)
                self.assertEqual("RANK", geometry["rankText"])
                self.assertEqual(1, geometry["rankRects"])
                self.assertGreaterEqual(geometry["podiumTop"], geometry["rankBottom"] - 4)
                self.assertLessEqual(geometry["podiumTop"], geometry["rankBottom"] + 8)
                self.assertGreaterEqual(
                    geometry["trophyWidth"], geometry["rankHeight"] * 0.82
                )
                self.assertTrue(
                    all(step["height"] >= 8 for step in geometry["podiumSteps"])
                )
                self.assertTrue(
                    all(step["textInside"] for step in geometry["podiumSteps"])
                )
                self.assertTrue(geometry["heartInside"])
                self.assertTrue(geometry["trophyInside"])
                context.close()

    def test_profile_identity_and_claim_are_above_the_fold(self) -> None:
        for width in (320, 375):
            with self.subTest(viewport=f"{width}x812"):
                context = self.browser.new_context(
                    viewport={"width": width, "height": 812},
                    locale="es-ES",
                )
                page = context.new_page()
                page.goto(
                    self.base_url + "?s=orslok&lang=es&qa=1&local=profile-identity",
                    wait_until="domcontentloaded",
                )
                page.locator("#section-view:not(.hidden) .profile-identity-main").wait_for(
                    state="visible"
                )
                result = page.evaluate(
                    """
                    () => {
                      const identity = document.querySelector('#profile-identity');
                      const claim = document.querySelector('.profile-claim');
                      const claimButton = document.querySelector('#claim-open');
                      const tags = document.querySelector('#profile-tags');
                      const status = document.querySelector('.profile-status');
                      const avatar = document.querySelector('.profile-avatar img, .profile-monogram');
                      const claimBox = claim.getBoundingClientRect();
                      const buttonBox = claimButton.getBoundingClientRect();
                      const suggestButtonBox = document.querySelector('#suggest-open').getBoundingClientRect();
                      const shareButtonBox = document.querySelector('#profile-share').getBoundingClientRect();
                      const titleBox = document.querySelector('#suggest-cta-title').getBoundingClientRect();
                      return {
                        claimParentIsIdentity: claim.parentElement === identity,
                        tagsInsideDetail: tags.parentElement.classList.contains('profile-identity-detail'),
                        hasStatus: Boolean(status && status.textContent.trim()),
                        hasAvatar: Boolean(avatar),
                        claimTop: claimBox.top,
                        buttonHeight: buttonBox.height,
                        suggestButtonWidth: suggestButtonBox.width,
                        suggestButtonBottom: suggestButtonBox.bottom,
                        shareButtonHeight: shareButtonBox.height,
                        focusOrderMatchesVisual: document.querySelector('#profile-share').compareDocumentPosition(document.querySelector('#suggest-open')) & Node.DOCUMENT_POSITION_FOLLOWING
                          ? shareButtonBox.right <= suggestButtonBox.left
                          : false,
                        buttonBelowTitle: suggestButtonBox.top >= titleBox.bottom,
                        titleWidth: titleBox.width,
                        suggestTop: suggestButtonBox.top
                      };
                    }
                    """
                )
                self.assertTrue(result["claimParentIsIdentity"])
                self.assertTrue(result["tagsInsideDetail"])
                self.assertTrue(result["hasStatus"])
                self.assertTrue(result["hasAvatar"])
                self.assertLess(result["claimTop"], 812)
                self.assertGreaterEqual(result["buttonHeight"], 44)
                self.assertGreaterEqual(result["suggestButtonWidth"], 180)
                self.assertLessEqual(result["suggestButtonBottom"], 812)
                self.assertGreaterEqual(result["shareButtonHeight"], 44)
                self.assertTrue(result["focusOrderMatchesVisual"])
                self.assertTrue(result["buttonBelowTitle"])
                self.assertGreaterEqual(result["titleWidth"], 240)
                self.assertLess(result["suggestTop"], 812)
                context.close()

    def test_verified_profile_does_not_reserve_an_empty_claim_column(self) -> None:
        context = self.browser.new_context(
            viewport={"width": 1440, "height": 1000},
            locale="es-ES",
        )
        page = context.new_page()
        page.goto(
            self.base_url + "?s=fanrank&lang=es&qa=1&local=verified-profile",
            wait_until="domcontentloaded",
        )
        page.locator("#profile-identity.is-verified").wait_for(state="visible")
        result = page.evaluate(
            """
            () => {
              const identity = document.querySelector('#profile-identity');
              const main = identity.querySelector('.profile-identity-main');
              const claim = identity.querySelector('.profile-claim');
              const identityBox = identity.getBoundingClientRect();
              const mainBox = main.getBoundingClientRect();
              return {
                gridColumns: getComputedStyle(identity).gridTemplateColumns.split(' ').length,
                mainCoverage: mainBox.width / identityBox.width,
                claimHidden: !claim || getComputedStyle(claim).display === 'none'
              };
            }
            """
        )
        self.assertEqual(1, result["gridColumns"])
        self.assertGreater(result["mainCoverage"], 0.9)
        self.assertTrue(result["claimHidden"])
        context.close()

    def test_home_shows_ranked_product_before_the_team_claim(self) -> None:
        context = self.browser.new_context(
            viewport={"width": 375, "height": 812},
            locale="es-ES",
        )
        page = context.new_page()
        page.goto(
            self.base_url + "?lang=es&qa=1&local=product-first",
            wait_until="domcontentloaded",
        )
        page.locator("#trending .trend-card").first.wait_for(state="visible")
        result = page.evaluate(
            """
            () => {
              const box = selector => document.querySelector(selector).getBoundingClientRect();
              const globalRank = box('.global-rank-block');
              const firstIdea = box('#trending .trend-card');
              const trust = box('#stats');
              const owner = box('#home-owner-verify');
              return {
                firstIdeaTop: firstIdea.top,
                trustAfterRank: trust.top >= globalRank.bottom,
                ownerAfterRank: owner.top >= globalRank.bottom,
                ownerAfterTrust: owner.top >= trust.bottom
              };
            }
            """
        )
        self.assertLess(result["firstIdeaTop"], 812)
        self.assertTrue(result["trustAfterRank"])
        self.assertTrue(result["ownerAfterRank"])
        self.assertTrue(result["ownerAfterTrust"])
        context.close()

    def test_reduced_motion_disables_brand_animation(self) -> None:
        context = self.browser.new_context(
            viewport={"width": 375, "height": 812},
            reduced_motion="reduce",
        )
        page = context.new_page()
        page.goto(
            self.base_url + "?lang=es&qa=1&local=reduced-motion",
            wait_until="domcontentloaded",
        )
        page.locator("[data-fanrank-logo]").wait_for(state="visible")
        animation_names = page.evaluate(
            """
            () => ['.logo-float','.brand-mark-heart:not(.emblem-shine)','.rank-trophy']
              .map(selector => getComputedStyle(document.querySelector(selector)).animationName)
            """
        )
        self.assertEqual(["none", "none", "none"], animation_names)
        context.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)

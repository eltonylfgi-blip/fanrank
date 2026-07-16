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
        for width, height in ((320, 812), (375, 812), (768, 900), (1440, 1000)):
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
                          isFirst: step.classList.contains('step-1'),
                          height: stepBox.height,
                          textInside: textBox.top >= stepBox.top - 1 && textBox.bottom <= stepBox.bottom + 1
                        };
                      });
                      const fanStyle = getComputedStyle(document.querySelector('.logo-fan'));
                      const rankStyle = getComputedStyle(document.querySelector('.rank-text'));
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
                        fanColor: fanStyle.color,
                        fanFill: fanStyle.webkitTextFillColor,
                        rankColor: rankStyle.color,
                        rankFill: rankStyle.webkitTextFillColor,
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
                # The enlarged podium deliberately overlaps the lower edge of R-A-N,
                # making those letters read as standing on places 2-1-3.
                self.assertGreaterEqual(geometry["podiumTop"], geometry["rankBottom"] - 9)
                self.assertLessEqual(geometry["podiumTop"], geometry["rankBottom"] + 8)
                self.assertGreaterEqual(
                    geometry["trophyWidth"], geometry["rankHeight"] * 1.25
                )
                transparent_values = {"transparent", "rgba(0, 0, 0, 0)"}
                self.assertNotIn(geometry["fanColor"], transparent_values)
                self.assertNotIn(geometry["fanFill"], transparent_values)
                self.assertNotIn(geometry["rankColor"], transparent_values)
                self.assertNotIn(geometry["rankFill"], transparent_values)
                # Edge occasionally reports a 12px CSS box as 11.9999847px after
                # sub-pixel layout. Keep the visual minimum without a float-equality flake.
                layout_epsilon = 0.01
                self.assertTrue(
                    all(
                        step["height"] + layout_epsilon
                        >= (16 if step["isFirst"] else 12)
                        for step in geometry["podiumSteps"]
                    )
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
              const trustElement = document.querySelector('#stats');
              const trustItems = [...trustElement.querySelectorAll('.trust-stat')];
              const owner = box('#home-owner-verify');
              return {
                firstIdeaTop: firstIdea.top,
                trustAfterRank: trust.top >= globalRank.bottom,
                trustColumns: getComputedStyle(trustElement).gridTemplateColumns.split(' ').filter(Boolean).length,
                trustItemsInside: trustItems.every(item => {
                  const itemBox = item.getBoundingClientRect();
                  return itemBox.left >= trust.left - 1 && itemBox.right <= trust.right + 1;
                }),
                teamTrustText: trustItems[2].textContent.trim(),
                ownerAfterRank: owner.top >= globalRank.bottom,
                ownerAfterTrust: owner.top >= trust.bottom
              };
            }
            """
        )
        self.assertLess(result["firstIdeaTop"], 812)
        self.assertTrue(result["trustAfterRank"])
        self.assertEqual(2, result["trustColumns"])
        self.assertTrue(result["trustItemsInside"])
        self.assertIn("El famoso o su equipo valora ideas", result["teamTrustText"])
        self.assertTrue(result["ownerAfterRank"])
        self.assertTrue(result["ownerAfterTrust"])
        context.close()

    def test_supported_home_vote_is_unmistakable_and_top_numbers_are_prominent(self) -> None:
        context = self.browser.new_context(
            viewport={"width": 375, "height": 812},
            locale="es-ES",
        )
        page = context.new_page()
        url = self.base_url + "?lang=es&qa=1&local=vote-state"
        page.goto(url, wait_until="domcontentloaded")
        first_vote = page.locator("[data-home-vote]").first
        first_vote.wait_for(state="visible")
        idea_id = first_vote.get_attribute("data-home-vote")
        self.assertIsNotNone(idea_id)
        page.evaluate(
            "ideaId => localStorage.setItem('fr_myvotes', JSON.stringify([Number(ideaId)]))",
            idea_id,
        )
        page.reload(wait_until="domcontentloaded")
        supported = page.locator(f'[data-home-vote="{idea_id}"]')
        supported.wait_for(state="visible")
        result = supported.evaluate(
            """
            button => {
              const style = getComputedStyle(button);
              const rgb = value => (value.match(/[0-9.]+/g) || []).slice(0,3).map(Number);
              const luminance = color => {
                const values = rgb(color).map(value => {
                  const channel = value / 255;
                  return channel <= .03928 ? channel / 12.92 : Math.pow((channel + .055) / 1.055, 2.4);
                });
                return .2126 * values[0] + .7152 * values[1] + .0722 * values[2];
              };
              const lighter = Math.max(luminance(style.color), luminance(style.backgroundColor));
              const darker = Math.min(luminance(style.color), luminance(style.backgroundColor));
              const cards = [...document.querySelectorAll('#trending .trend-card')];
              return {
                active: button.classList.contains('voted'),
                disabled: button.disabled,
                opacity: Number(style.opacity),
                contrast: (lighter + .05) / (darker + .05),
                text: button.textContent.replace(/\\s+/g, ' ').trim(),
                ariaLabel: button.getAttribute('aria-label'),
                rankClasses: cards.map(card => [...card.classList].find(name => name.startsWith('rank-'))),
                rankSizes: cards.map(card => parseFloat(getComputedStyle(card.querySelector('.trend-rank-number')).fontSize)),
                noOverflow: document.documentElement.scrollWidth === innerWidth
              };
            }
            """
        )
        self.assertTrue(result["active"])
        self.assertTrue(result["disabled"])
        self.assertEqual(1, result["opacity"])
        self.assertGreaterEqual(result["contrast"], 4.5)
        self.assertIn("✓", result["text"])
        self.assertIn("Apoyada", result["text"])
        self.assertTrue(result["ariaLabel"].startswith("Idea apoyada:"))
        self.assertEqual(["rank-1", "rank-2", "rank-3"], result["rankClasses"])
        self.assertTrue(all(size >= 28 for size in result["rankSizes"]))
        self.assertTrue(result["noOverflow"])
        context.close()

    def test_profile_ranking_keeps_top_three_prominent_and_rest_compact(self) -> None:
        context = self.browser.new_context(
            viewport={"width": 375, "height": 812},
            locale="es-ES",
        )
        page = context.new_page()
        page.goto(
            self.base_url + "?s=brawl-stars&lang=es&qa=1&local=rank-density",
            wait_until="domcontentloaded",
        )
        page.locator("#ideas-list .idea-card").nth(3).wait_for(state="visible")
        result = page.evaluate(
            """
            () => {
              const cards = [...document.querySelectorAll('#ideas-list .idea-card')];
              const top = cards.slice(0,3);
              const compact = cards[3];
              const detail = compact.querySelector('.idea-more');
              const summary = detail.querySelector('summary');
              const vote = compact.querySelector('.vote-btn');
              const meanTopHeight = top.reduce((sum, card) => sum + card.getBoundingClientRect().height, 0) / top.length;
              return {
                topRankSizes: top.map(card => parseFloat(getComputedStyle(card.querySelector('.rank')).fontSize)),
                topClasses: top.map(card => card.className),
                compactClass: compact.classList.contains('compact'),
                compactHeight: compact.getBoundingClientRect().height,
                meanTopHeight,
                detailCollapsed: !detail.open,
                summaryHeight: summary.getBoundingClientRect().height,
                voteWidth: vote.getBoundingClientRect().width,
                voteHeight: vote.getBoundingClientRect().height,
                noOverflow: document.documentElement.scrollWidth === innerWidth
              };
            }
            """
        )
        self.assertTrue(all(size >= 30 for size in result["topRankSizes"]))
        self.assertTrue(all(f"top{index}" in result["topClasses"][index - 1] for index in (1,2,3)))
        self.assertTrue(result["compactClass"])
        self.assertLessEqual(result["compactHeight"], 165)
        self.assertLess(result["compactHeight"], result["meanTopHeight"] * 0.72)
        self.assertTrue(result["detailCollapsed"])
        self.assertGreaterEqual(result["summaryHeight"], 44)
        self.assertGreaterEqual(result["voteWidth"], 44)
        self.assertGreaterEqual(result["voteHeight"], 44)
        self.assertTrue(result["noOverflow"])
        compact_summary = page.locator("#ideas-list .idea-card.compact .idea-more summary").first
        compact_summary.focus()
        page.keyboard.press("Enter")
        self.assertTrue(page.locator("#ideas-list .idea-card.compact .idea-more").first.evaluate("details => details.open"))
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

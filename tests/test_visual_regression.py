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
import time
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

    def test_share_dialog_fits_320_and_exposes_human_intents(self) -> None:
        context = self.browser.new_context(
            viewport={"width": 320, "height": 812},
            locale="es-ES",
        )
        page = context.new_page()
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(
            self.base_url + "?s=brawl-stars&lang=es&qa=1&local=cold-share",
            wait_until="domcontentloaded",
        )
        page.locator("#profile-share").wait_for(state="visible")
        page.locator("#profile-share").click()
        page.locator("#share-dialog[open]").wait_for(state="visible")
        result = page.evaluate(
            """
            () => {
              const dialog = document.querySelector('#share-dialog');
              const box = dialog.getBoundingClientRect();
              const text = document.querySelector('#share-preview').value;
              const previewLines = text.split('\\n');
              const sharedUrl = previewLines.pop();
              const shareText = previewLines.join('\\n');
              const x = document.querySelector('#share-x');
              const whatsapp = document.querySelector('#share-whatsapp');
              return {
                viewport: innerWidth,
                scrollWidth: document.documentElement.scrollWidth,
                dialogLeft: box.left,
                dialogRight: box.right,
                shareTextLength: shareText.length,
                sharedUrl,
                rankedLines: shareText.split('\\n').filter(line => /^\\d\\) /.test(line)).length,
                xHref: x.href,
                whatsappHref: whatsapp.href,
                xHeight: x.getBoundingClientRect().height,
                whatsappHeight: whatsapp.getBoundingClientRect().height,
                xTarget: x.target,
                whatsappTarget: whatsapp.target,
                xRel: x.rel,
                whatsappRel: whatsapp.rel
              };
            }
            """
        )
        self.assertEqual([], page_errors)
        self.assertLessEqual(result["scrollWidth"], result["viewport"])
        self.assertGreaterEqual(result["dialogLeft"], 0)
        self.assertLessEqual(result["dialogRight"], result["viewport"])
        self.assertLessEqual(result["shareTextLength"], 255)
        self.assertEqual(3, result["rankedLines"])
        self.assertIn("/fanrank/p/brawl-stars/", result["sharedUrl"])
        self.assertTrue(result["xHref"].startswith("https://x.com/intent/post?"))
        self.assertTrue(result["whatsappHref"].startswith("https://wa.me/?text="))
        self.assertGreaterEqual(result["xHeight"], 44)
        self.assertGreaterEqual(result["whatsappHeight"], 44)
        self.assertEqual("_blank", result["xTarget"])
        self.assertEqual("_blank", result["whatsappTarget"])
        self.assertIn("noopener", result["xRel"])
        self.assertIn("noopener", result["whatsappRel"])
        print(
            "[MEASURE] share_dialog_viewport=320 "
            f"scroll_width={result['scrollWidth']} text_chars={result['shareTextLength']}"
        )
        context.close()

    def test_anonymous_vote_stays_within_ten_seconds_from_cold_load(self) -> None:
        context = self.browser.new_context(
            viewport={"width": 320, "height": 812},
            locale="es-ES",
        )
        page = context.new_page()
        page_errors: list[str] = []
        vote_requests: list[dict] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        def intercept_vote(route) -> None:
            vote_requests.append(route.request.post_data_json)
            route.fulfill(status=204, headers={"Content-Length": "0"}, body="")

        page.route("**/rest/v1/fr_votes*", intercept_vote)
        started = time.perf_counter()
        page.goto(
            self.base_url + "?lang=es&qa=1&local=cold-anonymous-vote",
            wait_until="domcontentloaded",
        )
        vote_button = page.locator("[data-home-vote]").first
        vote_button.wait_for(state="visible")
        idea_id = vote_button.get_attribute("data-home-vote")
        self.assertIsNotNone(idea_id)
        vote_button.click()
        page.wait_for_function(
            """
            ideaId => JSON.parse(localStorage.getItem('fr_myvotes') || '[]')
              .includes(Number(ideaId))
            """,
            arg=idea_id,
        )
        elapsed_seconds = time.perf_counter() - started
        supported = page.locator(f'[data-home-vote="{idea_id}"]')
        supported.wait_for(state="visible")

        self.assertEqual([], page_errors)
        self.assertLessEqual(elapsed_seconds, 10)
        self.assertEqual(1, len(vote_requests))
        self.assertIsNone(vote_requests[0]["user_id"])
        self.assertTrue(str(vote_requests[0]["voter"]).startswith("v_"))
        self.assertTrue(supported.is_disabled())
        self.assertIn("Apoyada", supported.text_content())
        print(
            f"[MEASURE] cold_anonymous_vote_seconds={elapsed_seconds:.3f} "
            f"viewport=320 intercepted_writes={len(vote_requests)}"
        )
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

    def test_fan_offers_are_clear_touchable_and_separate_from_organic_rank(self) -> None:
        for width, height in ((320, 812), (375, 812), (768, 900), (1440, 1000)):
            with self.subTest(viewport=f"{width}x{height}"):
                context = self.browser.new_context(
                    viewport={"width": width, "height": height},
                    locale="es-ES",
                )
                page = context.new_page()
                page.goto(
                    self.base_url + "?lang=es&qa=1&local=fan-offers#fan-offers",
                    wait_until="domcontentloaded",
                )
                page.locator("#fan-offer-cards .fan-offer-card").first.wait_for(
                    state="visible"
                )
                result = page.evaluate(
                    """
                    () => {
                      const section = document.querySelector('#fan-offers');
                      const rail = section.querySelector('#fan-offer-cards');
                      const cards = [...section.querySelectorAll('.fan-offer-card')];
                      const buttons = [...section.querySelectorAll('[data-offer-interest]')];
                      const entity = document.querySelector('#entity-support');
                      const entityButton = entity.querySelector('#entity-support-interest');
                      const proPlans = document.querySelector('#pro-plans');
                      const pilot = document.querySelector('#pro-pilot-note');
                      const heading = section.querySelector('h2').getBoundingClientRect();
                      const topActions = document.querySelector('.top-actions');
                      const topActionsBox = topActions.getBoundingClientRect();
                      return {
                        cardCount: cards.length,
                        buttonCount: buttons.length,
                        minButtonHeight: Math.min(...buttons.map(button => button.getBoundingClientRect().height)),
                        founderText: cards[0].textContent.replace(/\\s+/g, ' ').trim(),
                        clubText: cards[1].textContent.replace(/\\s+/g, ' ').trim(),
                        sponsorText: cards[2].textContent.replace(/\\s+/g, ' ').trim(),
                        contractText: section.querySelector('.fan-offer-contract').textContent.replace(/\\s+/g, ' ').trim(),
                        entityText: entity.textContent.replace(/\\s+/g, ' ').trim(),
                        entityButtonHeight: entityButton.getBoundingClientRect().height,
                        entityBetweenPilotAndPlans: entity.previousElementSibling.classList.contains('pro-head') && entity.nextElementSibling === proPlans,
                        pilotText: pilot.textContent.replace(/\\s+/g, ' ').trim(),
                        planCount: proPlans.querySelectorAll('.pro-card').length,
                        sectionHeight: section.getBoundingClientRect().height,
                        railScrollable: rail.scrollWidth > rail.clientWidth + 2,
                        topActionsPosition: getComputedStyle(document.querySelector('.top-actions')).position,
                        topActionsCompact: topActions.classList.contains('compact'),
                        topActionsOverlapHeading: topActionsBox.bottom > heading.top && topActionsBox.top < heading.bottom && topActionsBox.right > heading.left && topActionsBox.left < heading.right,
                        noOverflow: document.documentElement.scrollWidth === innerWidth
                      };
                    }
                    """
                )
                self.assertEqual(3, result["cardCount"])
                self.assertEqual(3, result["buttonCount"])
                self.assertGreaterEqual(result["minButtonHeight"], 44)
                self.assertIn("5 €", result["founderText"])
                self.assertIn("pago único", result["founderText"])
                self.assertIn("SOLO 500", result["founderText"])
                self.assertIn("#N de 500", result["founderText"])
                self.assertIn("La suscripción abre un canal", result["clubText"])
                self.assertIn("ANUNCIO PAGADO", result["sponsorText"])
                self.assertIn("nunca compra", result["contractText"])
                self.assertIn("Apoyo de entidad", result["entityText"])
                self.assertIn("15 € o aportación libre", result["entityText"])
                self.assertIn("Todavía no se cobra", result["entityText"])
                self.assertIn("Apoyar no compra", result["entityText"])
                self.assertGreaterEqual(result["entityButtonHeight"], 44)
                self.assertTrue(result["entityBetweenPilotAndPlans"])
                self.assertIn("199 €", result["pilotText"])
                self.assertEqual(3, result["planCount"])
                self.assertLess(result["sectionHeight"], 900)
                self.assertEqual(width <= 900, result["railScrollable"])
                self.assertEqual("fixed", result["topActionsPosition"])
                self.assertTrue(result["topActionsCompact"])
                self.assertFalse(result["topActionsOverlapHeading"])
                self.assertTrue(result["noOverflow"])
                founder = page.locator('[data-offer-interest="fan_founder_5_once"]')
                founder.click()
                self.assertEqual("true", founder.get_attribute("aria-pressed"))
                self.assertIn("Interés guardado", founder.text_content())
                entity = page.locator('[data-offer-interest="entity_support_15_or_open"]')
                entity.scroll_into_view_if_needed()
                entity.click()
                self.assertEqual("true", entity.get_attribute("aria-pressed"))
                self.assertIn("Interés guardado", entity.text_content())
                context.close()

        context = self.browser.new_context(
            viewport={"width": 375, "height": 812},
            locale="es-ES",
        )
        page = context.new_page()
        for slug, expected_state in (
            ("orslok", "no puede abrir hasta que el perfil esté verificado"),
            ("fanrank", "deberá activar sus ventajas"),
        ):
            with self.subTest(profile=slug):
                page.goto(
                    self.base_url + f"?s={slug}&lang=es&qa=1&local=profile-club",
                    wait_until="domcontentloaded",
                )
                page.locator("#profile-club").wait_for(state="visible")
                profile_result = page.evaluate(
                    """
                    () => {
                      const club = document.querySelector('#profile-club');
                      const button = club.querySelector('#profile-club-interest');
                      return {
                        title: club.querySelector('#profile-club-title').textContent.trim(),
                        meta: club.querySelector('#profile-club-meta').textContent.trim(),
                        buttonHeight: button.getBoundingClientRect().height,
                        noOverflow: document.documentElement.scrollWidth === innerWidth
                      };
                    }
                    """
                )
                self.assertTrue(profile_result["title"].startswith("Club de "))
                self.assertIn(expected_state, profile_result["meta"])
                self.assertGreaterEqual(profile_result["buttonHeight"], 44)
                self.assertTrue(profile_result["noOverflow"])
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

    def test_existing_short_password_reaches_supabase_instead_of_client_block(self) -> None:
        context = self.browser.new_context(
            viewport={"width": 375, "height": 812}, locale="es-ES"
        )
        page = context.new_page()
        page_errors: list[str] = []
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.goto(
            self.base_url + "?lang=es&qa=1&local=auth-existing-password",
            wait_until="domcontentloaded",
        )
        page.evaluate(
            """
            () => {
              window.__authCalls = [];
              window.authClient = {auth:{signInWithPassword: async payload => {
                window.__authCalls.push(payload);
                return {data:{session:{user:{id:'browser-regression'}}},error:null};
              }}};
              openAuth('account');
              document.querySelector('#auth-password-panel').open = true;
            }
            """
        )
        page.locator("#auth-email").fill("legacy@example.com")
        page.locator("#auth-password").fill("1234567")
        page.locator("#auth-send").click()
        page.wait_for_function("window.__authCalls.length === 1")
        result = page.evaluate(
            """
            () => ({
              call: window.__authCalls[0],
              dialogOpen: document.querySelector('#auth-dialog').open,
              status: document.querySelector('#auth-status').textContent.trim()
            })
            """
        )
        self.assertEqual([], page_errors)
        self.assertEqual(
            {"email": "legacy@example.com", "password": "1234567"}, result["call"]
        )
        self.assertFalse(result["dialogOpen"])
        self.assertNotEqual("Completa el campo obligatorio.", result["status"])
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

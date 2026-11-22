"""Real-browser smoke test for the standalone Notcoin Observatory page."""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / ".qa"
WIDTHS = (360, 390, 768, 1280)


async def check():
    REPORT.mkdir(exist_ok=True)
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8765", "--bind", "127.0.0.1"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    rows = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                for width in WIDTHS:
                    context = await browser.new_context(
                        viewport={"width": width, "height": 840},
                        device_scale_factor=1
                    )
                    page = await context.new_page()
                    await page.goto("http://127.0.0.1:8765/index.html",
                                    wait_until="domcontentloaded", timeout=25000)
                    await page.locator("#market").wait_for()
                    await page.locator("#en").click()
                    assert await page.locator("html").get_attribute("lang") == "en", (
                        f"EN language switch failed at {width}"
                    )
                    await page.locator("#ru").click()
                    assert await page.locator("html").get_attribute("lang") == "ru", (
                        f"RU language switch failed at {width}"
                    )
                    toggle = page.locator("#badgeFilterToggle")
                    await toggle.click()
                    assert await toggle.get_attribute("aria-expanded") == "true", (
                        f"Badge filter did not open at {width}"
                    )
                    await toggle.click()
                    assert await toggle.get_attribute("aria-expanded") == "false", (
                        f"Badge filter did not close at {width}"
                    )
                    results = await page.evaluate("""() => {
                      const e = document.documentElement;
                      const anchors = [...document.querySelectorAll('a[href]')];
                      const bad = anchors.map(a => a.getAttribute('href'))
                        .filter(h => !h || /^javascript:/i.test(h) ||
                          !(h.startsWith('#') || /^https:\\/\\//i.test(h) ||
                            /^mailto:/i.test(h) || /^tel:/i.test(h)));
                      const externalAssets = [...document.querySelectorAll(
                        'script[src], link[rel="stylesheet"][href], iframe[src]'
                      )].map(e => e.outerHTML);
                      return {
                        viewport: innerWidth,
                        scrollWidth: e.scrollWidth,
                        links: anchors.length,
                        badLinks: bad,
                        externalAssets,
                        telegram: anchors.some(a =>
                          a.href === 'https://t.me/notcoin'),
                        title: document.title,
                        market: !!document.querySelector('#market'),
                        feed: !!document.querySelector('#feed'),
                        rankings: !!document.querySelector('#rank'),
                        mainLogoHero: getComputedStyle(document.querySelector('.heroArt'))
                          .backgroundImage.includes('data:image/webp;base64,'),
                        mainLogoHeader: getComputedStyle(document.querySelector('.brandMark'))
                          .backgroundImage.includes('data:image/webp;base64,'),
                        flagInTokenLabel: !!document.querySelector('[data-brand="project"] .brandGlyph') &&
                          getComputedStyle(document.querySelector('[data-brand="project"] .brandGlyph'))
                            .backgroundImage.includes('data:image/webp;base64,'),
                        compactTradeFlags: document.querySelectorAll(
                          '#feed .operationRow .opAmountUnit.tokenWithFlag .brandGlyph.brand-project'
                        ).length,
                        noTradeWatermarks: document.querySelectorAll(
                          '#feed .operationRow .operationWatermark'
                        ).length === 0,
                        roundHero: getComputedStyle(document.querySelector('.heroArt'))
                          .borderTopLeftRadius === '50%',
                        mainAndFlagSeparate: (() => {
                          const hero = getComputedStyle(document.querySelector('.heroArt')).backgroundImage;
                          const header = getComputedStyle(document.querySelector('.brandMark')).backgroundImage;
                          const mark = document.querySelector('[data-brand="project"] .brandGlyph');
                          return !!mark && hero === header &&
                            hero !== getComputedStyle(mark).backgroundImage;
                        })()
                      };
                    }""")
                    assert results["scrollWidth"] <= results["viewport"] + 2, (
                        f"Horizontal document overflow at {width}: {results}"
                    )
                    assert not results["badLinks"], f"Invalid anchors: {results['badLinks']}"
                    assert not results["externalAssets"], (
                        f"Runtime-loaded scripts/styles/iframes: {results['externalAssets']}"
                    )
                    assert results["telegram"], "Official Telegram link missing"
                    assert results["compactTradeFlags"] > 0 and results["noTradeWatermarks"], (
                        f"Trade flags are not compact or watermarks remain at {width}: {results}"
                    )
                    assert results["roundHero"], f"NOT hero logo is not rounded at {width}"
                    assert (results["mainLogoHero"] and results["mainLogoHeader"]
                            and results["flagInTokenLabel"] and results["mainAndFlagSeparate"]), (
                        f"Main logo or separate TONecoFlags #036 token marker missing at {width}: {results}"
                    )
                    assert all(results[k] for k in ("market", "feed", "rankings"))
                    assert "Notcoin" in results["title"], results["title"]
                    await page.screenshot(path=str(REPORT / f"mobile-{width}.png"))
                    rows.append({"width": width, **results, "status": "passed"})
                    print(f"{width}px: passed; {results['links']} links; "
                          f"scroll width {results['scrollWidth']}", flush=True)
                    await context.close()
            finally:
                await browser.close()
    finally:
        server.terminate()
        server.wait(timeout=8)
        (REPORT / "result.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2) + "\n"
        )


if __name__ == "__main__":
    asyncio.run(check())

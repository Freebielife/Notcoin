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
                        flagInTokenLabel: !!document.querySelector('[data-brand="notflag"] .brandGlyph') &&
                          getComputedStyle(document.querySelector('[data-brand="notflag"] .brandGlyph'))
                            .backgroundImage.includes('data:image/webp;base64,'),
                        compactTradeFlags: document.querySelectorAll(
                          '#feed .operationRow .opAmountUnit.tokenWithFlag .brandGlyph.brand-notflag'
                        ).length,
                        fiveLogoWatermarks: (() => {
                          const trades = [...document.querySelectorAll(
                            '#feed .operationRow.trade-buy, #feed .operationRow.trade-sell'
                          )];
                          const official = getComputedStyle(document.querySelector('.heroArt')).backgroundImage;
                          return trades.length > 0 && trades.every(card => {
                            const marks = [...card.querySelectorAll(
                              '.operationWatermark .brandGlyph.brand-project'
                            )];
                            return marks.length === 5 && marks.every(mark =>
                              getComputedStyle(mark).backgroundImage === official
                            );
                          });
                        })(),
                        noBurnWatermarks: document.querySelectorAll(
                          '#feed .operationRow.trade-burn .operationWatermark'
                        ).length === 0,
                        correctFlagsInPoolsAndLinks: (() => {
                          const flag = getComputedStyle(
                            document.querySelector('[data-brand="notflag"] .brandGlyph')
                          ).backgroundImage;
                          const poolFlags = [...document.querySelectorAll(
                            '#pools .knownPools .poolCard h3 .brandGlyph.brand-notflag'
                          )];
                          const notcoinSite = document.querySelector(
                            '#links .resourceList a[href="https://notcoin.org/"] .brandGlyph.brand-notflag'
                          );
                          return poolFlags.length >= 2 &&
                            poolFlags.every(node => getComputedStyle(node).backgroundImage === flag) &&
                            !!notcoinSite && getComputedStyle(notcoinSite).backgroundImage === flag;
                        })(),
                        roundHero: getComputedStyle(document.querySelector('.heroArt'))
                          .borderTopLeftRadius === '50%',
                        mainAndFlagSeparate: (() => {
                          const hero = getComputedStyle(document.querySelector('.heroArt')).backgroundImage;
                          const header = getComputedStyle(document.querySelector('.brandMark')).backgroundImage;
                          const mark = document.querySelector('[data-brand="notflag"] .brandGlyph');
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
                    assert (results["compactTradeFlags"] > 0 and
                            results["fiveLogoWatermarks"] and results["noBurnWatermarks"]), (
                        f"Five NOT background logos missing or incorrectly placed at {width}: {results}"
                    )
                    assert results["correctFlagsInPoolsAndLinks"], (
                        f"Incorrect NOT #036 flag in trading pools / useful links at {width}: {results}"
                    )
                    assert results["roundHero"], f"NOT hero logo is not rounded at {width}"
                    assert (results["mainLogoHero"] and results["mainLogoHeader"]
                            and results["flagInTokenLabel"] and results["mainAndFlagSeparate"]), (
                        f"Main logo or separate TONecoFlags #036 token marker missing at {width}: {results}"
                    )
                    assert all(results[k] for k in ("market", "feed", "rankings"))
                    assert "Notcoin" in results["title"], results["title"]
                    await page.screenshot(path=str(REPORT / f"mobile-{width}.png"))
                    # Actual rendered ranking must separate contracts and
                    # owner-supplied exchange labels from ordinary holders.
                    service_tab=page.locator("#views button").nth(2)
                    await service_tab.click()
                    service_text=await page.locator("#rank").inner_text()
                    assert "Binance" in service_text and "Bybit" in service_text, (
                        f"Operator-supplied exchange labels missing in service group at {width}"
                    )
                    assert "STON.fi DEX" in service_text, (
                        f"Primary Tonkeeper directory protocol label missing at {width}"
                    )
                    assert "Pavel Durov" not in service_text, (
                        f"Named individual incorrectly classified as service at {width}"
                    )
                    assert "Смарт-контракт" in service_text, (
                        f"Unattributed active contract not grouped as service at {width}"
                    )
                    await page.screenshot(path=str(REPORT / f"services-{width}.png"))
                    await page.locator("#views button").nth(0).click()
                    regular_text=await page.locator("#rank").inner_text()
                    person_entry=await page.evaluate("""() => {
                        const bootstrap=JSON.parse(document.querySelector('#snapshot').textContent);
                        const a='0:d8cd999fb2b1b384e6ca254c3883375e23111a8b78c015b886286c31bf11e29d';
                        return bootstrap.identity?.byWallet?.[a] || null;
                    }""")
                    assert person_entry and person_entry.get("directoryName") == "Pavel Durov", (
                        f"Tonkeeper name was not retained in bootstrap at {width}"
                    )
                    assert not person_entry.get("role"), (
                        f"External named person incorrectly moved to services at {width}"
                    )
                    assert "Binance" not in regular_text and "Bybit" not in regular_text, (
                        f"Exchange addresses still in normal holders at {width}"
                    )
                    assert "Смарт-контракт" not in regular_text, (
                        f"Unattributed contract still in normal holders at {width}"
                    )
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

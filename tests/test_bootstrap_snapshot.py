"""Prevent exponential size growth of published standalone TON Site."""
import json
import re
import unittest
from pathlib import Path

from scripts.bootstrap_snapshot import make_preview, MAX_PAGE_BYTES

ROOT = Path(__file__).resolve().parents[1]


class BootstrapTests(unittest.TestCase):
    def test_small_json_but_precise_holder_balances_and_roles(self):
        snap = json.loads((ROOT / "data/snapshot.json").read_text())
        preview = make_preview(snap)
        self.assertEqual(preview["token"], snap["token"])
        self.assertEqual(preview["holders"], snap["holders"])
        self.assertEqual(preview["identity"]["byWallet"]["0:f8b8635d0786b77f9da660e65fd31d670a675dd4302facba692f46b571eb5360"]["role"], "Binance")
        self.assertEqual(preview["identity"]["byWallet"]["0:cf7ea235ed6f6517edce98026ef7618e9f6d81a1331d4e65ba718e2cd15f80ad"]["role"], "Bybit")
        self.assertLessEqual(len(preview["trades"]["rows"]), 120)
        self.assertEqual(len(snap["trades"]["rows"]) > len(preview["trades"]["rows"]), True)
        self.assertGreaterEqual(preview["trades"]["since"], snap["trades"]["since"])
        self.assertNotIn("tradeHistory", preview)
        self.assertNotIn("accountTypes", preview)
        self.assertNotIn("serviceRegistry", preview)

    def test_bounded_html_and_embedded_preview(self):
        html = (ROOT / "index.html").read_text()
        self.assertLessEqual(len(html.encode("utf-8")), MAX_PAGE_BYTES)
        match = re.search(r'<script id="snapshot" type="application/json">(.*?)</script>', html, re.S)
        self.assertIsNotNone(match)
        preview = json.loads(match.group(1))
        self.assertEqual(preview["schema"], 1)
        self.assertLessEqual(len(preview["trades"]["rows"]), 120)
        self.assertEqual(preview["token"], json.loads((ROOT / "data/snapshot.json").read_text())["token"])

    def test_preview_never_misstates_trade_coverage(self):
        src = {
            "schema": 1, "token": "T", "updated": 2000, "errors": [],
            "trades": {"asOf": 2000, "since": 50, "rows": [
                {"wallet": "w1", "time": t, "tx": str(t)} for t in range(100, 200)]},
            "identity": {"asOf": 1900, "byWallet": {"w1": {"role": "Service"}, "w2": {}}},
        }
        preview = make_preview(src, trade_limit=2)
        self.assertEqual(len(preview["trades"]["rows"]), 2)
        self.assertEqual(preview["trades"]["since"], 198)
        self.assertEqual(list(preview["identity"]["byWallet"]), ["w1"])


if __name__ == "__main__":
    unittest.main()

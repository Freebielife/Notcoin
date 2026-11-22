"""Reject structurally invalid snapshots and look for a truncated packaged page."""
import json
import re
from decimal import Decimal
from pathlib import Path

from assets import MASTER
from trades import POOLS
from scripts.bootstrap_snapshot import make_preview, MAX_PAGE_BYTES, PREVIEW_TRADE_LIMITS

root = Path(__file__).resolve().parent
snapshot = json.loads((root / "data/snapshot.json").read_text())
assert snapshot["token"] == MASTER
assert snapshot["schema"] == 1 and snapshot.get("updated", 0) > 0
for key, kinds in (("trades", {"buy", "sell"}), ("burns", {"burn"})):
    if key not in snapshot:
        assert key in snapshot["errors"]
        continue
    section = snapshot[key]
    assert 0 < section["since"] <= section["asOf"]
    seen = set()
    for row in section["rows"]:
        assert row["kind"] in kinds and Decimal(row["tokenAmount"]) > 0
        assert re.fullmatch(r"[a-f0-9]{64}", row["tx"]) and row["tx"] not in seen
        assert re.fullmatch(r"-?\d+:[a-f0-9]{64}", row["wallet"])
        if key == "trades":
            assert Decimal(row["ton"]) > 0
            assert row["pool"] in POOLS and row["dex"] == POOLS[row["pool"]][1]
        seen.add(row["tx"])
if "holders" in snapshot:
    holders = snapshot["holders"]
    assert 0 < len(holders["holders"]) <= holders["holderCount"]
    for holder in holders["holders"]:
        expected = Decimal(holder["tokenAmount"]) * 100 / Decimal(holders["totalSupply"])
        assert abs(Decimal(str(holder["share"])) - expected) < Decimal("0.00000001")
if "rates" in snapshot:
    rates = snapshot["rates"]["rows"]
    assert len(rates) > 1
    assert all(a[0] < b[0] for a, b in zip(rates, rates[1:]))
    assert all(0 < price < 1000 for _, price in rates)
page = (root / "index.html").read_text()
payload = re.search(r'<script id="snapshot" type="application/json">(.*?)</script>', page, re.S)
assert payload, "Missing standalone bootstrap JSON"
embedded = json.loads(payload[1])
assert embedded["token"] == snapshot["token"]
assert embedded["updated"] == snapshot["updated"]
assert embedded["holders"] == snapshot["holders"]
assert embedded["trades"]["asOf"] == snapshot["trades"]["asOf"]
assert len(embedded["trades"]["rows"]) <= max(PREVIEW_TRADE_LIMITS)
assert embedded == make_preview(snapshot, trade_limit=len(embedded["trades"]["rows"]))
assert len(page.encode("utf-8")) <= MAX_PAGE_BYTES, "TON Site HTML size budget exceeded"
assert not any(token in page for token in ("/*APP*/", "/*STYLE*/", "/*LOADER*/", "/*MARKET_CAP*/", "__PROJECT_ART__"))
print("Snapshot and standalone page validated.")

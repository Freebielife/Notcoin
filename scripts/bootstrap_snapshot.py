"""Create a bounded offline preview, while preserving the full GitHub snapshot.

The standalone TON Site is not a 10,000-trade archive. Its embedded JSON must
remain small, with the current full verified snapshot retrieved from GitHub.
"""
from __future__ import annotations

MAX_PAGE_BYTES = 512_000
PREVIEW_TRADE_LIMITS = (120, 90, 60, 30, 0)
PREVIEW_RATE_LIMIT = 45
PREVIEW_BURN_LIMIT = 40


def _section(snapshot, key):
    value = snapshot.get(key)
    return dict(value) if isinstance(value, dict) else None


def make_preview(snapshot, *, trade_limit=90):
    if not isinstance(trade_limit, int) or trade_limit < 0 or trade_limit > 120:
        raise ValueError("Invalid trade preview limit")
    result = {key: snapshot[key] for key in ("schema", "token", "updated", "errors")
              if key in snapshot}
    wallets = set()

    holders = _section(snapshot, "holders")
    if holders:
        result["holders"] = holders
        wallets.update(r["wallet"] for r in holders.get("holders", []))

    for section_name, limit in (("trades", trade_limit),
                                ("burns", PREVIEW_BURN_LIMIT),
                                ("zeroBurns", PREVIEW_BURN_LIMIT)):
        original = _section(snapshot, section_name)
        if not original:
            continue
        rows = sorted(original.get("rows", []),
                      key=lambda row: (-int(row.get("time", 0)), str(row.get("tx", ""))))[:limit]
        section = {**original, "rows": rows}
        if "since" in original:
            # A partial preview never claims historical coverage that it lacks.
            section["since"] = max(
                int(original["since"]),
                min((int(row["time"]) for row in rows), default=int(original.get("asOf", 0))))
        result[section_name] = section
        wallets.update(r["wallet"] for r in rows)

    for section_name in ("identity", "domains", "fragmentNumbers"):
        original = _section(snapshot, section_name)
        if not original:
            continue
        data = original.get("byWallet", {})
        result[section_name] = {**original, "byWallet": {
            w: item for w, item in data.items() if w in wallets}}

    rates = _section(snapshot, "rates")
    if rates:
        result["rates"] = {**rates, "rows": rates.get("rows", [])[-PREVIEW_RATE_LIMIT:]}

    badges = _section(snapshot, "badges")
    if badges:
        slim_sources = {}
        for badge_name, entry in badges.get("sources", {}).items():
            slim_sources[badge_name] = {**entry, "wallets": {
                w: proof for w, proof in entry.get("wallets", {}).items()
                if w in wallets}}
        result["badges"] = {**badges, "sources": slim_sources}

    # Metadata and market pools contain no historical event archive.
    # Source registry, accountTypes and tradeHistory aren't used by the UI and
    # are deliberately excluded from the offline preview.
    for section_name in ("pools", "vesting", "staking"):
        original = _section(snapshot, section_name)
        if original:
            result[section_name] = original

    return result

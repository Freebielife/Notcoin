"""Shared TON custodial labels, attributed to Tonkeeper's curated address book.

Exact address matches only. Labels are external attribution, not on-chain proof
of ownership. No inference from account names, balances or counterparties.
"""
import hashlib
import json
import re
from pathlib import Path

SOURCE = "https://raw.githubusercontent.com/tonkeeper/ton-assets/main/accounts.json"
SOURCE_PAGE = "https://github.com/tonkeeper/ton-assets/blob/main/accounts.json"
INTERVAL = 86400
ADDRESS = re.compile(r"(?:0|-1):[0-9a-f]{64}")
# Only these custodial families from the curated book qualify as services.
# Anchored suffixes exclude unrelated names that merely mention an exchange.
FAMILIES = (
    "Binance", "OKX", "Bybit", "MEXC", "Gate.io", "Bitget", "Kucoin",
    "Huobi", "HTX", "BingX", "Bitfinex", "CoinEx", "Crypto.com", "EXMO",
    "FTX", "BitMart", "Nobitex", "Bitpin", "Coinone", "Paribu", "TIDEX",
    "QMall", "BIT", "Bitforex", "OMPFinex", "Bitrue", "Coinspot", "BigOne",
    "Farhad Exchange", "BitTime", "Foxbit", "Richamster", "Flipster", "Ourbit",
    "lbank.info", "bit.com", "Crypto Bot", "CryptoBot", "Wallet Bot",
    "Wallet in Telegram", "xRocket Bot", "CWallet", "Matrixport",
)
NAME = re.compile(r"(?:" + "|".join(re.escape(n) for n in FAMILIES) +
                  r")(?:\s*(?:\d+|Hot Wallet|Cold Storage(?: \d+)?|Deposit|Withdrawal))?"
                  r"(?: \(Old\))?", re.I)
# Exact labels from TONkeeper that represent protocol infrastructure rather
# than individuals. Matching names alone is insufficient: role assignment
# additionally requires the exact normalized on-chain address.
PROTOCOLS = (
    r"DeDust [\w₮-]+ vault",
    r"DeDust Pool: [\w₮/$.-]+",
    r"STON\.fi DEX",
    r"Omniston (?:Escrow Minter|Fee Vault|DEX Bridge)",
    r"Notcoin Voucher Swap [0-9A-F]",
    r"(?:BSC|ETH) Bridge(?: (?:Collector|Governance))?",
    r"Orbit Bridge (?:TON|ETH|KLAYTN|POLYGON|WEMIX) (?:Vault|Governance|Minter)",
    r"Symbiosis Bridge",
    r"(?:Getgems|Portals|Disintar) Marketplace",
    r"Getgems Gift Minter",
)
PROTOCOL = re.compile(r"(?:" + "|".join(PROTOCOLS) + r")", re.I)


def service_name(name):
    return bool(NAME.fullmatch(name) or PROTOCOL.fullmatch(name))


def parse_directory(accounts):
    """Full first-party address directory. Conflicting aliases are quarantined."""
    if not isinstance(accounts, list) or not 1 <= len(accounts) <= 20000:
        raise ValueError("Malformed curated account list")
    directory, conflicting = {}, set()
    for row in accounts:
        if not isinstance(row, dict):
            raise ValueError("Malformed curated account")
        addr, name = row.get("address"), row.get("name")
        if not isinstance(addr, str) or not ADDRESS.fullmatch(addr):
            raise ValueError("Invalid curated address")
        if not isinstance(name, str) or not name or len(name) > 256:
            raise ValueError("Invalid curated label")
        if addr in directory and directory[addr] != name:
            conflicting.add(addr)
        else:
            directory[addr] = name
    for addr in conflicting:
        directory.pop(addr, None)
    if not directory:
        raise ValueError("Empty or ambiguous curated directory")
    return directory, sorted(conflicting)


def parse_accounts(accounts):
    directory, _ = parse_directory(accounts)
    entries = {addr: name for addr, name in directory.items() if service_name(name)}
    if not entries:
        raise ValueError("Empty service registry")
    return entries


def validate(registry):
    if (registry.get("source") != SOURCE_PAGE or
            not isinstance(registry.get("asOf"), int) or registry["asOf"] <= 0 or
            not re.fullmatch(r"[0-9a-f]{64}", registry.get("sha256", ""))):
        raise ValueError("Invalid registry provenance")
    entries = registry.get("entries")
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Missing registry entries")
    parsed = parse_accounts([{"address": a, "name": n} for a, n in entries.items()])
    if parsed != entries:
        raise ValueError("Unsupported registry label")
    directory = registry.get("directory")
    if directory is not None:
        if not isinstance(directory, dict) or not directory or len(directory) > 20000:
            raise ValueError("Invalid full Tonkeeper directory")
        for addr, name in directory.items():
            if not ADDRESS.fullmatch(addr) or not isinstance(name, str) or not name:
                raise ValueError("Malformed Tonkeeper directory item")
        if any(directory.get(a) != n for a, n in entries.items()):
            raise ValueError("Service registry disagrees with full Tonkeeper directory")
    return registry


def bundled():
    return validate(json.loads(Path(__file__).with_name("common-services.json").read_text()))


def lookup(wallet, registry=None):
    return (registry if registry is not None else bundled())["entries"].get(wallet)


def refresh(previous, now, fetch=None):
    previous = validate(previous) if previous else bundled()
    if now - previous["asOf"] < INTERVAL:
        return previous
    if fetch is None:
        from assets import fetch
    accounts = fetch("", attempts=2, api=SOURCE)
    directory, ambiguous = parse_directory(accounts)
    entries = {address: name for address, name in directory.items() if service_name(name)}
    digest = hashlib.sha256(json.dumps(accounts, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False).encode()).hexdigest()
    return {"asOf": now, "source": SOURCE_PAGE, "sha256": digest,
            "entries": entries, "directory": directory,
            "ambiguous": ambiguous, "sourceCount": len(accounts)}


def apply(snapshot, registry, overrides=None):
    """Label the entire tracked address set without spending per-wallet API quota."""
    overrides = overrides or {}
    registry = validate(registry)
    identity = snapshot.setdefault("identity", {"byWallet": {}})
    records = identity.setdefault("byWallet", {})
    wallets = set(records)
    for section, key in (("holders", "holders"), ("trades", "rows"),
                         ("burns", "rows"), ("zeroBurns", "rows")):
        wallets.update(r["wallet"] for r in snapshot.get(section, {}).get(key, []))
    for wallet in wallets:
        # TONkeeper verified exact address first, supplementary labels second.
        label = lookup(wallet, registry) or overrides.get(wallet)
        record = records.get(wallet, {})
        directory_name = registry.get("directory", {}).get(wallet)
        if directory_name:
            record["directoryName"] = directory_name
            record["directorySource"] = SOURCE_PAGE
        else:
            record.pop("directoryName", None)
            record.pop("directorySource", None)
        if record.pop("roleRegistry", False):
            # A removed upstream attribution must not survive in the identity cache.
            record.update(role=None)
            record.pop("roleSource", None)
            record.pop("roleChecked", None)
        if label:
            record["role"] = label
            if wallet in registry["entries"]:
                record.update(roleRegistry=True, roleSource=registry["source"],
                              roleChecked=registry["asOf"])
        # Named persons are labelled for display but must not be moved into
        # the service ranking unless they match the curated service subset.
        if record:
            records[wallet] = record


def update(snapshot, now, overrides=None):
    """Retain last good labels on source failure, without falsifying their age."""
    registry = snapshot.get("serviceRegistry") or bundled()
    # Older Notcoin snapshots contain only 112 custody labels, despite using
    # the same upstream blob. Rehydrate its complete source-derived catalog
    # before calling remote services, without changing asOf/source timestamps.
    local = bundled()
    if (registry.get("source") == SOURCE_PAGE and
            len(registry.get("directory", {})) < len(local.get("directory", {})) and
            all(local["entries"].get(k) == v for k, v in registry["entries"].items())):
        # Old refreshes omitted sourceBlob, so comparing only that field missed
        # the upgrade whenever upstream access failed. The local directory is
        # committed from the exact official accounts.json and is authoritative
        # for all its 235 service entries; keep its original verification time.
        registry = local
    try:
        registry = refresh(registry, now)
        error = None
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        error = type(exc).__name__
        print("Service registry refresh unavailable:", error, flush=True)
    snapshot["serviceRegistry"] = registry
    apply(snapshot, registry, overrides)
    return error

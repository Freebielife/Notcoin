"""Identify deployed non-wallet contracts without inferring their operator.

The service/contract ranking is a display group. 'unclassified_contract'
does not mean a verified exchange, custodian or protocol owner.
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from decimal import Decimal
from urllib.request import Request, urlopen

from assets import raw_address
import observatory
import service_registry

SOURCE = "https://tonapi.io/v2/accounts/_bulk"
CHECK_INTERVAL = 6 * 3600


def scope(snapshot):
    holders = [r["wallet"] for r in snapshot.get("holders", {}).get("holders", [])[:100]]
    trades = snapshot.get("trades", {})
    as_of = int(trades.get("asOf", 0))
    sold = defaultdict(int)
    for row in trades.get("rows", []):
        if row.get("kind") != "sell" or not as_of - 30 * 86400 < int(row.get("time", 0)) <= as_of:
            continue
        sold[row["wallet"]] += int(Decimal(row["tokenAmount"]) * 10**9)
    sellers = sorted(sold, key=lambda address: (-sold[address], address))[:40]
    return list(dict.fromkeys([*holders, *sellers]))


def fetch_bulk(addresses):
    req = Request(SOURCE, method="POST",
                  data=json.dumps({"account_ids": addresses}).encode("utf-8"),
                  headers={"Content-Type": "application/json", "Accept": "application/json",
                           "User-Agent": "NOT-Observatory-Contract-Grouping/1.0"})
    with urlopen(req, timeout=24) as response:
        data = json.load(response)
    accounts = data.get("accounts") if isinstance(data, dict) else None
    if not isinstance(accounts, list):
        raise ValueError("TonAPI account bulk response malformed")
    result = {}
    for row in accounts:
        address = raw_address(row["address"])
        if address not in addresses or not isinstance(row.get("is_wallet"), bool):
            raise ValueError("Unexpected TON account")
        status = str(row.get("status", ""))
        if status not in ("active", "uninit", "nonexist", "frozen"):
            raise ValueError("Unexpected TON account state")
        interfaces = row.get("interfaces", [])
        if not isinstance(interfaces, list) or not all(isinstance(v, str) for v in interfaces):
            raise ValueError("Malformed contract interfaces")
        result[address] = {"isWallet": row["is_wallet"], "status": status,
                           "interfaces": interfaces[:16]}
    if set(result) != set(addresses):
        raise ValueError("TonAPI returned incomplete account list")
    return result


def collect(snapshot, previous, now):
    tracked = scope(snapshot)
    cache = dict(previous.get("byWallet", {}))
    due = [wallet for wallet in tracked
           if now - int(cache.get(wallet, {}).get("checkedAt", 0)) >= CHECK_INTERVAL]
    for start in range(0, len(due), 20):
        batch = due[start:start+20]
        for attempt in range(3):
            try:
                result = fetch_bulk(batch)
                break
            except (OSError, KeyError, TypeError, ValueError):
                if attempt == 2:
                    raise
                time.sleep(2 ** (attempt + 1))
        for address, data in result.items():
            cache[address] = dict(data, checkedAt=now)
        if start + 20 < len(due):
            time.sleep(0.5)
    return {"asOf": now, "source": SOURCE,
            "byWallet": {address: cache[address] for address in tracked if address in cache}}


def apply(snapshot, now):
    identities = snapshot.setdefault("identity", {}).setdefault("byWallet", {})
    registry = snapshot.get("serviceRegistry") or service_registry.bundled()
    trusted = observatory.KNOWN_SERVICES
    declared = observatory.USER_DECLARED_SERVICES
    targets = set(scope(snapshot))
    for address, item in snapshot.get("accountTypes", {}).get("byWallet", {}).items():
        if address not in targets:
            continue
        record = identities.setdefault(address, {})
        record["accountIsWallet"] = item["isWallet"]
        record["accountStatus"] = item["status"]
        if address in declared or address in trusted or service_registry.lookup(address, registry):
            continue
        if item["status"] == "active" and item["isWallet"] is False:
            if not record.get("role") or record["role"] == "unclassified_contract":
                record["role"] = "unclassified_contract"
                record["roleSource"] = SOURCE
                record["roleChecked"] = item.get("checkedAt", now)
        elif record.get("role") == "unclassified_contract":
            record["role"] = None
            if record.get("roleSource") == SOURCE:
                record.pop("roleSource", None)
                record.pop("roleChecked", None)
    # Explicit user-submitted custodial attributions, NOT independently verified
    # by TonAPI account metadata, keep their own source and highest priority.
    for address, label in declared.items():
        record = identities.setdefault(address, {})
        record["role"] = label
        record["roleSource"] = observatory.USER_LABEL_SOURCE
        record["roleChecked"] = now
        record.pop("roleRegistry", None)

"""Exact custodial attribution, shared export and failure-safe refresh tests."""
import copy
import unittest
from unittest.mock import patch

import service_registry as registry
import observatory


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.book = registry.bundled()
        self.wallet = next(a for a, n in self.book["entries"].items() if n == "Binance")
        self.now = self.book["asOf"] + registry.INTERVAL + 1

    def test_exact_address_not_account_name_is_evidence(self):
        self.assertEqual(observatory.role(self.wallet, {"is_wallet": True}), "Binance")
        self.assertIsNone(observatory.role("0:" + "ef" * 32,
                                          {"is_wallet": True, "name": "Binance"}))
        self.assertIsNone(registry.lookup("0:" + "ff" * 32))

    def test_all_holders_are_attributed_without_network_or_budget(self):
        snap = {"holders": {"holders": [{"wallet": self.wallet}]},
                "identity": {"byWallet": {self.wallet: {"checked": self.now}}}}
        with patch("assets.fetch", side_effect=AssertionError("No account request allowed")):
            registry.apply(snap, self.book)
        record = snap["identity"]["byWallet"][self.wallet]
        self.assertEqual(record["role"], "Binance")
        self.assertEqual(record["checked"], self.now)
        self.assertEqual(record["roleSource"], registry.SOURCE_PAGE)

    def test_daily_refresh_validates_and_removes_upstream_labels(self):
        other = "0:" + "ab" * 32
        rows = [{"address": other, "name": "OKX 99"}]
        snap = {"holders": {"holders": [{"wallet": self.wallet}]}}
        registry.apply(snap, self.book)
        fresh = registry.refresh(self.book, self.now, fetch=lambda *a, **kw: rows)
        registry.apply(snap, fresh)
        self.assertIsNone(snap["identity"]["byWallet"][self.wallet]["role"])
        self.assertNotIn("roleSource", snap["identity"]["byWallet"][self.wallet])
        self.assertEqual(registry.lookup(other, fresh), "OKX 99")
        self.assertEqual(fresh["asOf"], self.now)

    def test_cached_custody_catalog_upgrades_without_network(self):
        old = copy.deepcopy(self.book)
        old["entries"] = {a: n for a, n in old["entries"].items()
                          if not n.startswith("STON.fi") and
                          not n.startswith("DeDust")}
        old.pop("directory", None)
        old.pop("sourceBlob", None)
        person = "0:d8cd999fb2b1b384e6ca254c3883375e23111a8b78c015b886286c31bf11e29d"
        dex = "0:f1fbe8d453d3d4b4796d3d8657ef0773222d123d8dca67c9ef3acd2266f40977"
        snap = {"serviceRegistry": old, "holders": {"holders": [
            {"wallet": person}, {"wallet": dex}]}}
        with patch("assets.fetch", side_effect=OSError("temporary source error")):
            self.assertEqual(registry.update(snap, self.now), "OSError")
        self.assertEqual(len(snap["serviceRegistry"]["directory"]), 538)
        self.assertEqual(registry.lookup(dex, snap["serviceRegistry"]), "STON.fi DEX")
        self.assertEqual(snap["identity"]["byWallet"][person]["directoryName"], "Pavel Durov")
        self.assertEqual(snap["identity"]["byWallet"][dex]["role"], "STON.fi DEX")
        self.assertIsNone(snap["identity"]["byWallet"][person].get("role"))

    def test_refresh_waits_one_day(self):
        with patch("assets.fetch", side_effect=AssertionError("Too early")):
            self.assertEqual(registry.refresh(self.book, self.now - 2), self.book)

    def test_failed_source_preserves_labels_and_original_time(self):
        snap = {"serviceRegistry": copy.deepcopy(self.book),
                "holders": {"holders": [{"wallet": self.wallet}]}}
        with patch("assets.fetch", side_effect=OSError("unavailable")):
            self.assertEqual(registry.update(snap, self.now), "OSError")
        self.assertEqual(snap["serviceRegistry"], self.book)
        self.assertEqual(snap["identity"]["byWallet"][self.wallet]["role"], "Binance")

    def test_unrelated_names_invalid_addresses_and_conflicts(self):
        for rows in ([], {}, [{"address": "broken", "name": "OKX 1"}],
                     [{"address": self.wallet, "name": "Binance"},
                      {"address": self.wallet, "name": "OKX 1"}],
                     [{"address": self.wallet, "name": "Binance fan club"}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                registry.parse_accounts(rows)

    def test_tonkeeper_primary_and_manual_fallback(self):
        unknown = "0:" + "fa" * 32
        snap = {"holders": {"holders": [{"wallet": self.wallet}, {"wallet": unknown}]}}
        registry.apply(snap, self.book, {
            self.wallet: "Wrong override", unknown: "Owner-confirmed fallback"})
        records = snap["identity"]["byWallet"]
        self.assertEqual(records[self.wallet]["role"], "Binance")
        self.assertEqual(records[self.wallet]["roleSource"], registry.SOURCE_PAGE)
        self.assertEqual(records[unknown]["role"], "Owner-confirmed fallback")
        self.assertNotIn("roleRegistry", records[unknown])

    def test_directory_is_first_checked_and_nonservices_not_misclassified(self):
        full = registry.bundled()
        self.assertGreaterEqual(len(full["directory"]), 500)
        self.assertGreaterEqual(len(full["entries"]), 200)
        dex = "0:f1fbe8d453d3d4b4796d3d8657ef0773222d123d8dca67c9ef3acd2266f40977"
        person = "0:d8cd999fb2b1b384e6ca254c3883375e23111a8b78c015b886286c31bf11e29d"
        self.assertEqual(registry.lookup(dex, full), "STON.fi DEX")
        self.assertIsNone(registry.lookup(person, full))
        self.assertEqual(full["directory"][person], "Pavel Durov")
        self.assertNotIn("0:94a7cf34ef6a4b5063500975d70c524cdc2e6ff465d38d5ee8bb7dcc8f7af45e", full["directory"])

    def test_nonservice_directory_name_survives_without_service_role(self):
        person = "0:d8cd999fb2b1b384e6ca254c3883375e23111a8b78c015b886286c31bf11e29d"
        snap = {"holders": {"holders": [{"wallet": person}]}}
        registry.apply(snap, self.book)
        record = snap["identity"]["byWallet"][person]
        self.assertEqual(record["directoryName"], "Pavel Durov")
        self.assertEqual(record["directorySource"], registry.SOURCE_PAGE)
        self.assertIsNone(record.get("role"))

    def test_tonkeeper_duplicate_addresses_are_quarantined(self):
        ambiguous = "0:" + "aa" * 32
        rows = [{"address": ambiguous, "name": "TON Coin Pool Rewards"},
                {"address": ambiguous, "name": "TON Coin Pool Withdraw 1"},
                {"address": "0:" + "bb" * 32, "name": "STON.fi DEX"}]
        directory, duplicates = registry.parse_directory(rows)
        self.assertNotIn(ambiguous, directory)
        self.assertEqual(duplicates, [ambiguous])
        self.assertEqual(registry.parse_accounts(rows), {"0:" + "bb"*32: "STON.fi DEX"})


if __name__ == "__main__":
    unittest.main()

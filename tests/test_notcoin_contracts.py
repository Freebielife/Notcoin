"""No service owner may be invented from a wallet or contract type."""
import unittest
from unittest.mock import patch
import observatory
from scripts import notcoin_contracts as classifier


class ContractTypesTests(unittest.TestCase):
    def setUp(self):
        self.wallets = ["0:" + x * 64 for x in ("a", "b", "c")]
        self.now = 1795350000
        self.snapshot = {
            "holders": {"holders": [{"wallet": w} for w in self.wallets]},
            "identity": {"byWallet": {}},
            "accountTypes": {"asOf": self.now, "source": classifier.SOURCE, "byWallet": {
                self.wallets[0]: {"isWallet": False, "status": "active", "interfaces": [], "checkedAt": self.now},
                self.wallets[1]: {"isWallet": True, "status": "active", "interfaces": ["wallet_highload_v3r1"], "checkedAt": self.now},
                self.wallets[2]: {"isWallet": True, "status": "uninit", "interfaces": [], "checkedAt": self.now},
            }}
        }

    def test_only_deployed_nonwallet_contract_moves_to_service_group(self):
        classifier.apply(self.snapshot, self.now)
        records = self.snapshot["identity"]["byWallet"]
        self.assertEqual(records[self.wallets[0]]["role"], "unclassified_contract")
        self.assertEqual(records[self.wallets[0]]["roleSource"], classifier.SOURCE)
        self.assertNotIn("role", records[self.wallets[1]])
        self.assertNotIn("role", records[self.wallets[2]])

    def test_known_protocol_contract_preserved(self):
        wallet = next(iter(observatory.KNOWN_SERVICES))
        self.snapshot["holders"]["holders"].append({"wallet": wallet})
        self.snapshot["accountTypes"]["byWallet"][wallet] = {
            "isWallet": False, "status": "active", "interfaces": [], "checkedAt": self.now}
        self.snapshot["identity"]["byWallet"][wallet] = {"role": observatory.KNOWN_SERVICES[wallet]}
        classifier.apply(self.snapshot, self.now)
        self.assertEqual(self.snapshot["identity"]["byWallet"][wallet]["role"],
                         observatory.KNOWN_SERVICES[wallet])

    def test_existing_metadata_cache_requires_no_network(self):
        with patch.object(classifier, "fetch_bulk", side_effect=AssertionError("cache not used")):
            result = classifier.collect(
                self.snapshot, {"byWallet": self.snapshot["accountTypes"]["byWallet"]}, self.now)
        self.assertEqual(len(result["byWallet"]), 3)


if __name__ == "__main__":
    unittest.main()

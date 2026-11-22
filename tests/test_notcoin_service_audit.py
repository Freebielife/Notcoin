"""Verify NOT protocol address labels are exact, never inferred from balance."""
import unittest
import observatory


class NotcoinServiceAuditTests(unittest.TestCase):
    def test_exact_identified_service_wallets(self):
        known = {
            "0:779dcc815138d9500e449c5291e7f12738c23d575b5310000f6a253bd607384e": "STON.fi DEX",
            "0:06f3f073c255a49aa6fdcc89abf512638e065908b30e4173fd3d1d01d4f607bd": "Storm Trade Vault",
        }
        for wallet, name in known.items():
            with self.subTest(wallet=wallet):
                self.assertEqual(observatory.KNOWN_SERVICES[wallet], name)
                self.assertEqual(observatory.role(wallet, {"is_wallet": False}), name)

    def test_generic_contract_is_unclassified_not_named(self):
        self.assertEqual(
            observatory.role("0:" + "ef" * 32, {"status": "active", "is_wallet": False}),
            "unclassified_contract",
        )
        self.assertIsNone(observatory.role("0:" + "dd" * 32, {"is_wallet": True}))


if __name__ == "__main__":
    unittest.main()

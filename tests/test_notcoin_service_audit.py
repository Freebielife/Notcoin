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

    def test_operator_supplied_binance_bybit_addresses(self):
        self.assertEqual(observatory.USER_DECLARED_SERVICES[
            "0:f8b8635d0786b77f9da660e65fd31d670a675dd4302facba692f46b571eb5360"], "Binance")
        self.assertEqual(observatory.USER_DECLARED_SERVICES[
            "0:cf7ea235ed6f6517edce98026ef7618e9f6d81a1331d4e65ba718e2cd15f80ad"], "Bybit")
        for wallet, name in observatory.USER_DECLARED_SERVICES.items():
            self.assertEqual(observatory.role(wallet, {"is_wallet": True}), name)

    def test_generic_contract_is_unclassified_not_named(self):
        self.assertEqual(
            observatory.role("0:" + "ef" * 32, {"status": "active", "is_wallet": False}),
            "unclassified_contract",
        )
        self.assertIsNone(observatory.role("0:" + "dd" * 32, {"is_wallet": True}))


if __name__ == "__main__":
    unittest.main()

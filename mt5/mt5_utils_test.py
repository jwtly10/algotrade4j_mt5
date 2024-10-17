import unittest
import os
from dotenv import load_dotenv
from mt5.mt5_utils import get_trades_for_account, build_open_trade_from_position_id
from mt5.mt5_instance import init_mt5_instance
import json

load_dotenv()


class MetaTraderAPITestCase(unittest.TestCase):
    def setUp(self):
        self.mock_account_id = int(os.getenv("TEST_ACCOUNT_ID"))
        self.mock_password = os.getenv("TEST_PASSWORD")
        self.mock_server = os.getenv("TEST_SERVER")
        self.mock_path = os.getenv("TEST_MT5_PATH")
        self.mock_api_key = os.getenv("AUTH_API_KEY")

    def test_get_historic_trades(self):
        init_mt5_instance(
            self.mock_account_id, self.mock_password, self.mock_server, self.mock_path
        )

        res = get_trades_for_account(self.mock_account_id)

        print(json.dumps(res, indent=4))

        self.assertTrue(len(res) > 1)

    def test_build_trade_from_position_id(self):
        init_mt5_instance(
            self.mock_account_id, self.mock_password, self.mock_server, self.mock_path
        )

        res = build_open_trade_from_position_id(183415689)

        print(json.dumps(res, indent=4))

        self.assertIsNotNone(res["position_id"])
        self.assertIsNotNone(res["symbol"])
        self.assertIsNotNone(res["total_volume"])
        self.assertIsNotNone(res["profit"])


if __name__ == "__main__":
    unittest.main()

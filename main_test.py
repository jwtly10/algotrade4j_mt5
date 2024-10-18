import unittest
from unittest.mock import patch
import json
import os
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from main import app
from mt5.mt5_instance import init_mt5_instance
from internal_types import TradeRequest

load_dotenv()

client = TestClient(app)


class MetaTraderAPITestCase(unittest.TestCase):
    def setUp(self):
        self.client = client

        self.mock_account_id = int(os.getenv("TEST_ACCOUNT_ID"))
        self.mock_password = os.getenv("TEST_PASSWORD")
        self.mock_server = os.getenv("TEST_SERVER")
        self.mock_path = os.getenv("TEST_MT5_PATH")
        self.mock_api_key = os.getenv("AUTH_API_KEY")

    def test_initialize_mt5(self):
        response = self.client.post(
            "api/v1/initialize",
            json={
                "accountId": self.mock_account_id,
                "password": self.mock_password,
                "server": self.mock_server,
                "path": self.mock_path,
            },
            headers={"x-api-key": self.mock_api_key},
        )

        data = response.json()
        print("Response was: ")
        print(json.dumps(data, indent=4))

        self.assertEqual(response.status_code, 200)
        self.assertIn("initialized", data["status"])
        self.assertIn(f"{self.mock_account_id}", data["message"])

    def test_initialize_mt5_fail(self):
        response = self.client.post(
            "api/v1/initialize",
            json={
                "accountId": self.mock_account_id,
                "password": self.mock_password,
                "server": self.mock_server,
                "path": "C:/Users/failed/Programs/MetaTrader 5/terminal64.exe",  # This is invalid
            },
            headers={"x-api-key": self.mock_api_key},
        )

        data = response.json()
        print("Response was: ")
        print(json.dumps(data, indent=4))

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            "Failed to initialize MT5 instance: Error code: -10003, Reason: IPC initialize failed, Process create failed 'C:/Users/failed/Programs/MetaTrader 5/terminal64.exe'",
            data["detail"],
        )

    def test_get_account_info(self):
        init_mt5_instance(
            self.mock_account_id, self.mock_password, self.mock_server, self.mock_path
        )

        response = self.client.get(
            f"api/v1/accounts/{self.mock_account_id}",
            headers={"x-api-key": self.mock_api_key},
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        print("Response was: ")
        print(json.dumps(data, indent=4))

        self.assertIn("login", data)
        self.assertEqual(self.mock_account_id, data["login"])
        self.assertIsNotNone(data["equity"])
        self.assertIsNotNone(data["balance"])
        self.assertIsNotNone(data["server"])
        self.assertIsNotNone(data["company"])
        self.assertIsNotNone(data["profit"])

    def test_get_trades(self):
        init_mt5_instance(
            self.mock_account_id, self.mock_password, self.mock_server, self.mock_path
        )

        response = self.client.get(
            f"api/v1/trades/{self.mock_account_id}",
            headers={"x-api-key": self.mock_api_key},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        print("Response was: ")
        print(json.dumps(data, indent=4))

        if len(data["trades"]) > 0:
            self.assertIsInstance(data["trades"], list)
        else:
            self.assertEqual({}, data["trades"])

    def test_open_trade(self):
        init_mt5_instance(
            self.mock_account_id, self.mock_password, self.mock_server, self.mock_path
        )

        mock_req_body: TradeRequest = {
            "instrument": "US100.cash",
            "quantity": 0.1,
            "entryPrice": {"value": 20202.85},
            "stopLoss": {"value": 20172.85},
            "takeProfit": {"value": 20262.75},
            "riskPercentage": 0.001,
            "riskRatio": 2.0,
            "balanceToRisk": 10000.0,
            "isLong": True,
            "openTime": "something",
        }

        response = self.client.post(
            f"api/v1/trades/{self.mock_account_id}/open",
            json=mock_req_body,
            headers={"x-api-key": self.mock_api_key},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        print("Response was: ")
        print(json.dumps(data, indent=4))

        self.assertIsNotNone(data["position_id"])
        self.assertIsNotNone(data["symbol"])
        self.assertIsNotNone(data["total_volume"])
        self.assertIsNotNone(data["is_open"])
        self.assertIsNotNone(data["is_long"])
        self.assertIsNotNone(data["open_order_ticket"])
        self.assertIsNotNone(data["open_order_time"])
        self.assertIsNotNone(data["stop_loss"])
        self.assertIsNotNone(data["take_profit"])
        self.assertIsNotNone(data["profit"])

    def test_close_trade(self):
        init_mt5_instance(
            self.mock_account_id, self.mock_password, self.mock_server, self.mock_path
        )

        mocked_trade_id = 184102117  # You need to manually open this to pass the test

        response = self.client.post(
            f"api/v1/trades/{self.mock_account_id}/close/{mocked_trade_id}",
            headers={"x-api-key": self.mock_api_key},
        )

        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()

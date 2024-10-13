import unittest
import json
import os
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from main import app
from mt5_instance import init_mt5_instance
import logging

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

client = TestClient(app)


class MetaTraderAPITestCase(unittest.TestCase):
    def setUp(self):
        self.client = client

        self.mock_account_id = int(os.getenv("TEST_ACCOUNT_ID"))
        self.mock_password = os.getenv("TEST_PASSWORD")
        self.mock_server = os.getenv("TEST_SERVER")
        self.mock_path = os.getenv("TEST_MT5_PATH")

    def test_initialize_mt5(self):
        response = self.client.post(
            "/account/initialize",
            json={
                "accountId": self.mock_account_id,
                "password": self.mock_password,
                "server": self.mock_server,
                "path": self.mock_path,
            },
        )

        data = response.json()
        print("Sending response: ")
        print(json.dumps(data, indent=4))

        self.assertEqual(response.status_code, 200)
        self.assertIn("initialized", data["status"])
        self.assertIn(f"{self.mock_account_id}", data["message"])

    def test_initialize_mt5_fail(self):
        response = self.client.post(
            "/account/initialize",
            json={
                "accountId": self.mock_account_id,
                "password": self.mock_password,
                "server": self.mock_server,
                "path": "C:/Users/failed/Programs/MetaTrader 5/terminal64.exe",  # This is invalid
            },
        )

        data = response.json()
        print("Sending response: ")
        print(json.dumps(data, indent=4))

        self.assertEqual(response.status_code, 500)
        self.assertIn("failed", data["status"])
        self.assertEqual(
            "Failed to initialize MetaTrader instance: Error code: -10003, Reason: IPC initialize failed, Process create failed 'C:/Users/failed/Programs/MetaTrader 5/terminal64.exe'",
            data["message"],
        )

    def test_get_account_info(self):
        init_mt5_instance(
            self.mock_account_id, self.mock_password, self.mock_server, self.mock_path
        )

        response = self.client.get(f"/account/get-account/{self.mock_account_id}")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        print("Sending response: ")
        print(json.dumps(data, indent=4))

        self.assertIn("login", data)
        self.assertEqual(self.mock_account_id, data["login"])

    def test_get_trades(self):
        init_mt5_instance(
            self.mock_account_id, self.mock_password, self.mock_server, self.mock_path
        )

        response = self.client.get(f"/trades/get-trades/{self.mock_account_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        print("Sending response: ")
        print(json.dumps(data, indent=4))

        if len(data["trades"]) > 0:
            self.assertIsInstance(data["trades"], list)
        else:
            self.assertEqual({}, data["trades"])


if __name__ == "__main__":
    unittest.main()

import unittest
import json
import os
from dotenv import load_dotenv
from app import app, init_mt5_instance, instances, closed_trades_cache 
import logging

load_dotenv()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MetaTraderAPITestCase(unittest.TestCase):
    
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

        self.mock_account_id = int(os.getenv('TEST_ACCOUNT_ID'))
        self.mock_password = os.getenv('TEST_PASSWORD')
        self.mock_server = os.getenv('TEST_SERVER')
        self.mock_path = os.getenv('TEST_MT5_PATH')
    
    def test_initialize_mt5(self):
        response = self.app.post('/initialize', 
            data=json.dumps({
                "accountId": self.mock_account_id,
                "password": self.mock_password,
                "server": self.mock_server,
                "path": self.mock_path
            }),
            content_type='application/json'
        )

        data = json.loads(response.data)
        print("Sending response: ")
        print(json.dumps(data, indent=4))

        self.assertEqual(response.status_code, 200)
        self.assertIn("initialized", data["status"])
        self.assertIn(f"{self.mock_account_id}", data["message"])


    def test_initialize_mt5_fail(self):
        response = self.app.post('/initialize', 
            data=json.dumps({
                "accountId": self.mock_account_id,
                "password": self.mock_password,
                "server": self.mock_server,
                "path": "C:/Users/failed/Programs/MetaTrader 5/terminal64.exe" # This is invalid
            }),
            content_type='application/json'
        )

        data = json.loads(response.data)
        print("Sending response: ")
        print(json.dumps(data, indent=4))

        self.assertEqual(response.status_code, 500)
        self.assertIn("failed", data["status"])
        self.assertEqual("Failed to initialize MetaTrader instance: Error code: -10003, Reason: IPC initialize failed, Process create failed 'C:/Users/failed/Programs/MetaTrader 5/terminal64.exe'", data["message"])

    
    def test_get_account_info(self):
        init_mt5_instance(self.mock_account_id, self.mock_password, self.mock_server, self.mock_path)

        response = self.app.get(f'/get-account/{self.mock_account_id}')
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        print("Sending response: ")
        print(json.dumps(data, indent=4))

        self.assertIn("login", data)
        self.assertEqual(self.mock_account_id, data["login"])


    def test_get_trades(self):
        init_mt5_instance(self.mock_account_id, self.mock_password, self.mock_server, self.mock_path)

        # Test getting all trades
        response = self.app.get(f'/get-trades/{self.mock_account_id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        print("Sending response: ")
        print(json.dumps(data, indent=4))

        if len(data["trades"]) > 0:
            # Verify trades data is returned in a list
            self.assertIsInstance(data, list)
            # TODO: Validate the actual trade object
        else:
            self.assertEqual({},data["trades"])

    def test_open_trade(self):
        # Mock initialization first
        init_mt5_instance(self.mock_account_id, self.mock_password, self.mock_server, self.mock_path)

        # Simulate opening a trade
        response = self.app.post(f'/open-trade/{self.mock_account_id}', 
            data=json.dumps({
                "symbol": "EURUSD",
                "volume": 0.1,
                "order_type": 0,  # 0 for buy, 1 for sell
                "stop_loss": 1.1500,
                "take_profit": 1.2000
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("order", data)

    def test_close_trade(self):
        # Mock initialization first
        init_mt5_instance(self.mock_account_id, self.mock_password, self.mock_server, self.mock_path)

        # Simulate closing a trade (assuming ticket 12345 for simplicity)
        response = self.app.post(f'/close-trade/{self.mock_account_id}', 
            data=json.dumps({
                "ticket": 12345,
                "symbol": "EURUSD"
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("retcode", data)

    def test_closed_trades_stream(self):
        # Mock initialization first
        init_mt5_instance(self.mock_account_id, self.mock_password, self.mock_server, self.mock_path)

        # Simulate getting the closed trades stream
        response = self.app.get(f'/closed-trades-stream/{self.mock_account_id}', 
            content_type='text/event-stream'
        )
        
        # Since this is a stream, we'll just check the status code
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()

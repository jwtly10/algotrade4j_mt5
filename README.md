# MT5 Adapter for Algotrade4J

This is a MetaTrader 5 (MT5) adapter for the Algotrade4J algorithmic trading platform. It acts as a broker-style REST interface for MT5 instances, enabling the Algotrade4j Platform to communicate with MT5 Accounts.

This is a WIP adapter and not ready for production use yet.


### TODO: 
- Get account data (v0)
- Get all trades for account (v0)
- Open trade (v0)
- Close trade (v0)
- Stream transactions (Open, Close) (TODO)

#### Deployment:
TODO: Current implementation works for only a single instance running on a windows server
Need to support mutliple MT5 Instances (each with different account)


### Notes:
Requirements: 
- Python 3.8.x (Tested on 3.8.10)
- Windows (Tested on self hosted Windows 11) but should be supported down to Windows 7

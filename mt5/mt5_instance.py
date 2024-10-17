import MetaTrader5 as mt5
from typing import Tuple, Optional
from utils.logging import get_logger

log = get_logger(__name__)

instances = {}


def init_mt5_instance(
    accountId: int, password: str, server: str, path: str
) -> Tuple[bool, Optional[Tuple[int, str]]]:
    """
    Initializes an MT5 instance with given account credentials.

    :param accountId: The account ID (int)
    :param password: The account password (string)
    :param server: The server name (string)
    :param path: The path to the MT5 installation (string)
    :return: A tuple with a success flag (boolean) and an optional error (tuple of error code and message)
    """
    log.info(f"Initializing MT5 Account {accountId}")
    if not mt5.initialize(login=accountId, password=password, server=server, path=path):
        error = mt5.last_error()
        return False, error
    instances[accountId] = {"login": accountId, "server": server, "path": path}
    return True, None


def get_mt5_instance(account_id: int):
    """
    Checks if given account_id is a valid account that has been initialised
    """
    if account_id not in instances:
        log.error(
            f"Account id {account_id} not found in instances. May not have been initialised"
        )
        return None
    return instances[account_id]

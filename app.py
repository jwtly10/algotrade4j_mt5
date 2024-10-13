from flask import Flask, request, jsonify, Response
import MetaTrader5 as mt5
import time
from datetime import datetime, timedelta
import logging
from typing import Tuple, Optional, Union

import validation

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

app = Flask(__name__)

instances = {}
closed_trades_cache = {}


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
    if not mt5.initialize(login=accountId, password=password, server=server, path=path):
        error = mt5.last_error()
        return False, error
    instances[accountId] = {"login": accountId, "server": server, "path": path}
    closed_trades_cache[accountId] = {}
    return True, None


@app.route("/initialize", methods=["POST"])
def initialize():
    """
    Initializes a MetaTrader 5 (MT5) account using provided account credentials.

    Request Body (JSON):
    - accountId: The account ID (int) required for login
    - password: The password (string) associated with the account
    - server: The server (string) where the account is hosted
    - path: The path (string) to the local MetaTrader 5 installation

    Responses:
    - 200 OK: When the account is successfully initialized, returns a JSON response with the status "initialized"
      and a success message.
      Example:
      {
          "status": "initialized",
          "message": "Successfully initialized account with id: <accountId>"
      }

    - 400 Bad Request: If the input parameters are invalid, returns a JSON response indicating the validation errors.
      Example:
      {
          "status": "failed",
          "message": "Invalid account parameters"
      }

    - 500 Internal Server Error: If an error occurs during initialization, either due to an MT5 error or an
      unexpected exception, returns a JSON response with the status "failed" and the corresponding error message.
      Example:
      {
          "status": "failed",
          "message": "Failed to initialize MetaTrader instance: Error code: <code>, Reason: <reason>"
      }
    """
    data = request.json
    accountId = data["accountId"]
    password = data["password"]
    server = data["server"]
    path = data["path"]

    validation_error = validation.validate_initialise_params(
        accountId, password, server, path
    )
    if validation_error:
        return jsonify(validation_error), 400

    log.info(f"Initializing MT5 Account {accountId}")

    try:
        success, error = init_mt5_instance(accountId, password, server, path)
        if success:
            log.info(f"Successfully initialized account %s", accountId)
            return jsonify(
                {
                    "status": "initialized",
                    "message": f"Succesfully initialized account with id: {accountId}",
                }
            ), 200
        else:
            err_str = log_error(
                error, f"/initialize [POST] with accountID: {accountId}"
            )
            return jsonify(
                {
                    "status": "failed",
                    "message": f"Failed to initialize MetaTrader instance: {err_str}",
                }
            ), 500
    except Exception as e:
        log.error("Exception on /initialize [POST]", exc_info=True)
        return jsonify(
            {
                "status": "failed",
                "message": "An unexpected error occurred during initialization.",
            }
        ), 500


def get_mt5_instance(accountId: int) -> Union[bool, Tuple[Response, int]]:
    """
    Retrieves the MetaTrader 5 (MT5) instance for a given account ID.

    :param accountId: The account ID (int) for which the MT5 instance is being requested.
    :return: Returns True if the instance exists. If not, returns a tuple containing a JSON response with an error message
             and a 404 HTTP status code.
    """
    if accountId not in instances:
        log.error(f"Account id {accountId} not found in instances")
        return jsonify(
            {
                "status": "failed",
                "message": f"MT5 instance not initialized for account {accountId}",
            }
        ), 404
    return True


@app.route("/get-account/<int:accountId>", methods=["GET"])
def get_account(accountId: int) -> Tuple[Response, int]:
    """
    Fetches account information for a specific MetaTrader 5 (MT5) account.

    :param accountId: The account ID (int) for which the account information is being fetched.

    :return: A JSON response containing the account information if successful, or an error message with the corresponding HTTP status code.

    Response:
    - 200 OK: Returns the account information as a JSON object with the following structure:
      Example:
      {
          "assets": 0.0,
          "balance": 10000.0,
          "commission_blocked": 0.0,
          "company": "FTMO S.R.O.",
          "credit": 0.0,
          "currency": "USD",
          "currency_digits": 2,
          "equity": 10000.0,
          "fifo_close": false,
          "leverage": 100,
          "liabilities": 0.0,
          "limit_orders": 200,
          "login": 1510057641,
          "margin": 0.0,
          "margin_free": 10000.0,
          "margin_initial": 0.0,
          "margin_level": 0.0,
          "margin_maintenance": 0.0,
          "margin_mode": 2,
          "margin_so_call": 100.0,
          "margin_so_mode": 0,
          "margin_so_so": 50.0,
          "name": "FTMO Free Trial USD",
          "profit": 0.0,
          "server": "FTMO-Demo",
          "trade_allowed": true,
          "trade_expert": true,
          "trade_mode": 0
      }
    """
    log.info(f"Getting account info for account {accountId}")
    instance_check = get_mt5_instance(accountId)

    # If the instance_check is not True, it means an error response is returned
    if instance_check is not True:
        return instance_check

    # Fetch account info from MetaTrader 5
    account = mt5.account_info()
    error = mt5.last_error()
    if account:
        return jsonify(account._asdict()), 200
    else:
        err_str = log_error(
            error, "/get-account/<int:accountId> [GET] with accountId: {accountId}"
        )
        return jsonify(
            {
                "status": "failed",
                "message": f"Failed to fetch account information: {err_str}",
            }
        ), 500


@app.route("/get-trades/<int:accountId>", methods=["GET"])
def get_trades(accountId):
    """
    Fetches open trades for a specific MetaTrader 5 (MT5) account.

    :param accountId: The account ID (int) for which trades are being requested.

    :return: A JSON response with the following structure:

    - 200 OK: If trades are successfully fetched.
      Example:
      {
          "status": "success",
          "trades": [<list of trade dictionaries>]
      }
      If no trades are found, an empty dictionary will be returned:
      {
          "status": "success",
          "trades": {}
      }
    """
    instance_check = get_mt5_instance(accountId)
    if instance_check != True:
        return instance_check

    trades = mt5.positions_get()
    error = mt5.last_error()
    if trades is not None and len(trades) > 0:
        trades_list = [trade._asdict() for trade in trades]
        return jsonify({"status": "success", "trades": trades_list}), 200
    elif trades is None:
        err_str = log_error(
            error, f"/get-trades/<int:accountId> [GET] with accountId: {accountId}"
        )
        return jsonify(
            {"status": "failed", "message": f"Failed to fetch trades: {err_str}"}
        ), 500
    else:
        return jsonify({"status": "success", "trades": {}}), 200


@app.route("/open-trade/<int:accountId>", methods=["POST"])
def open_trade(accountId):
    """
    Note 13th Oct 2024:
    Our current implementation does not support using data directly form the MT5 Instance. We use external data providers
    that closesly resemble the data from the broker, however data may not match up perfectly. Therefore we need to change how
    we actually trigger new trades when connecting to a MT5 terminal


    The current implementation provides an interface to open a trade at the current price, give a specific stop
    loss size, and delegates logic for generating the trade values to the python adapter.
    data:
    {
    "instrument":"inst",
    "quantity": 0.00,
    "entryPrice":
        {
            value: 10000
        },
    "stopLoss":
        {
            value: 9000
        },
    "takeProfit":
        {
            value: 12000
        },
    "riskPercentage": 0.3,
    "riskRatio": 2,
    "balanceToRisk": 10000,
    "isLong": 0.3,
    "openTime": "something"
    }

    How it works is, it will take the price given by the caller, and if within a given tolerance (TODO)
    will execute the trade with the same setup at market price

    Take the above data example

    The platform has already done its own logic based on the data provided to generate its own trade,
    and now we need to match it up correctly to the real data we have from the broker:

    1. Figure out the stop loss pips - abs(entryPrice-stoplossprice)
    2. Create a new stop loss based on current market price, using isLong as bid/ask flag
    3. Using the riskRatio create a new take profit based on the stop loss pips
    4. Generate quantity based on balance to risk & riskPercentage, and the given stop loss
    5. Execute trade



    """
    instance_check = get_mt5_instance(accountId)
    if instance_check != True:
        return instance_check

    data = request.json
    symbol = data["instrument"]
    risk_percentage = data["riskPercentage"]
    balance_to_risk = data["balanceToRisk"]
    stop_loss_input = data["stopLoss"]["value"]
    entry_price = data["entryPrice"]["value"]
    take_profit_input = data["takeProfit"]["value"]
    risk_ratio = data["riskRatio"]
    is_long = data["isLong"] == 1

    symbol_info = mt5.symbol_info_tick(symbol)
    if not symbol_info:
        return jsonify({"status": "failed", "message": "Symbol not found"}), 404

    current_price = symbol_info.ask if is_long else symbol_info.bid

    stop_loss_pips = abs(entry_price - stop_loss_input)

    if is_long:
        new_stop_loss = current_price - stop_loss_pips
    else:
        new_stop_loss = current_price + stop_loss_pips

    new_take_profit_pips = stop_loss_pips * risk_ratio
    if is_long:
        new_take_profit = current_price + new_take_profit_pips
    else:
        new_take_profit = current_price - new_take_profit_pips

    # TODO: Pip value conversion from Algotrade4j to Adapter
    risk_amount = balance_to_risk * risk_percentage
    volume = risk_amount / (stop_loss_pips * 10)

    order_type = mt5.ORDER_TYPE_BUY if is_long else mt5.ORDER_TYPE_SELL
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": current_price,
        "sl": new_stop_loss,
        "tp": new_take_profit,
    }

    result = mt5.order_send(request)

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        return jsonify(result._asdict()), 200
    else:
        error = mt5.last_error()
        err_str = log_error(
            error,
            f"/open-trade/<int:accountId> [POST] with accountId: {accountId} and data: {data}",
        )
        return jsonify(
            {
                "status": "failed",
                "message": f"Failed to open trade: [{result.retcode if result else "Unknown Error"}] {err_str}",
                "error_code": result.retcode if result else "Unknown error",
            }
        ), 500


# TODO
@app.route("/close-trade/<int:accountId>", methods=["POST"])
def close_trade(accountId):
    instance_check = get_mt5_instance(accountId)
    if instance_check != True:
        return instance_check

    data = request.json
    ticket = data["ticket"]
    symbol = data["symbol"]
    position = mt5.positions_get(ticket=ticket)

    if not position:
        return jsonify({"status": "failed", "message": "Trade not found"}), 404

    close_type = (
        mt5.ORDER_TYPE_SELL
        if position[0].type == mt5.ORDER_TYPE_BUY
        else mt5.ORDER_TYPE_BUY
    )
    close_price = (
        mt5.symbol_info_tick(symbol).bid
        if close_type == mt5.ORDER_TYPE_SELL
        else mt5.symbol_info_tick(symbol).ask
    )

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": position[0].volume,
        "type": close_type,
        "price": close_price,
    }

    result = mt5.order_send(request)

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        return jsonify(result._asdict()), 200
    return jsonify({"status": "failed", "message": "Failed to close trade"}), 500


# TODO
@app.route("/transactions-stream/<int:accountId>", methods=["GET"])
def closed_trades_stream(accountId):
    instance_check = get_mt5_instance(accountId)
    if instance_check != True:
        return instance_check

    def generate_closed_trades(accountId):
        while True:
            time.sleep(1)
            now = time.time()
            closed_trades = mt5.history_deals_get(
                datetime.now() - timedelta(seconds=1), datetime.now()
            )

            if closed_trades:
                for trade in closed_trades:
                    if trade.ticket not in closed_trades_cache[accountId]:
                        closed_trades_cache[accountId][trade.ticket] = now
                        yield f"data: {trade._asdict()}\n\n"

    return Response(generate_closed_trades(accountId), content_type="text/event-stream")


def log_error(err: Tuple[int, str], action: str) -> str:
    """
    Logs an error message and returns a formatted error string.

    :param err: A tuple containing the error code (int) and the error message (str).
    :param action: The action that failed (str)

    :return: A formatted string describing the error in the form:
             "Error code: <error_code>, Reason: <error_message>"

    Logs:
    - Error: Logs an error with the format "Error during <action>: Error code: <error_code>, Reason: <error_message>" to indicate the failure
      during operations.
    """
    err_str = f"Error code: {err[0]}, Reason: {err[1]}"
    log.error(f"Error during '{action}': {err_str}")
    return err_str


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

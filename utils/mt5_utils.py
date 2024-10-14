from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import HTTPException
import json
import MetaTrader5 as mt5
import logging

from routes.trades import TradesList
from routes.trades import Trade
from utils.utils import log_error

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)


def get_historic_trades(accountId: int) -> TradesList:
    list_of_trades: TradesList = []

    start_time = datetime(2024, 1, 1)
    end_time = datetime.now() + timedelta(
        days=1
    )  # To get around any timezone differences

    orders = mt5.history_orders_get(start_time, end_time)
    err = mt5.last_error()
    if orders == None:
        err_str = log_error(
            err, f"/trades/<accountId> [GET] with accountId: {accountId}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get historic trades: {err_str}"
        )

    position_id_orders = defaultdict(list)

    for trade in orders:
        trade_dict = trade._asdict()
        position_id_orders[trade_dict["position_id"]].append(trade_dict)

    for position_id, order_list in position_id_orders.items():
        # Generic data
        combined_trade: Trade = {
            "position_id": position_id,
            "symbol": order_list[0]["symbol"],
            "total_volume": order_list[0]["volume_initial"],
        }

        # All trades have a buy and sell order
        order_buy = {}
        order_sell = {}

        for order in order_list:
            if (
                order["type"] == 0
            ):  # ORDER_TYPE_BUY https://www.mql5.com/en/docs/constants/tradingconstants/orderproperties#enum_order_type
                order_buy = order
            elif (
                order["type"] == 1
            ):  # ORDER_TYPE_SELL https://www.mql5.com/en/docs/constants/tradingconstants/orderproperties#enum_order_type
                order_sell = order
            else:
                print(
                    f"NEW ORDER TYPE FOUND - THIS HAS NOT BEEN HANDLED BY THE ADAPTER: {order}"
                )

        if order_buy != {} and order_sell == {}:
            # This is an open trade, this means the open ticket was created but theres a chance there
            open_position = mt5.positions_get(
                ticket=order_buy["ticket"] if order_buy else order_sell["ticket"]
            )
            err = mt5.last_error()
            if open_position is None:
                err_str = log_error(
                    err, f"/trades/<accountId> [GET] with accountId: {accountId}"
                )
                raise HTTPException(
                    status_code=500, detail=f"Failed to get historic trades: {err_str}"
                )

            pos_dict = open_position[0]._asdict()

            combined_trade["is_long"] = True if pos_dict["type"] == 0 else False
            combined_trade["open_order_ticket"] = pos_dict["ticket"]
            combined_trade["open_order_price"] = pos_dict["price_open"]
            combined_trade["open_order_time"] = pos_dict["time"]
            combined_trade["stop_loss"] = pos_dict["sl"]
            combined_trade["take_profit"] = pos_dict["tp"]
            combined_trade["profit"] = round(
                pos_dict["profit"]
                + pos_dict.get("swap", 0)
                + pos_dict.get("commission", 0),
                2,
            )

            list_of_trades.append(combined_trade)
            continue

        elif order_buy == {} or order_sell == {}:
            log.debug(
                f"This should not happen - order_buy: {json.dumps(order_buy, indent=4)}, order_sell: {json.dumps(order_sell, indent=4)}"
            )

        isLong = order_buy["time_done"] < order_sell["time_done"]
        combined_trade["is_long"] = isLong

        combined_trade["open_order_ticket"] = (
            order_buy["ticket"] if isLong else order_sell["ticket"]
        )
        # If the order was long, we can use the buy order to set open/close data
        combined_trade["open_order_price"] = (
            order_buy["price_current"] if isLong else order_sell["price_current"]
        )
        combined_trade["open_order_time"] = (
            order_buy["time_done"] if isLong else order_sell["time_done"]
        )

        combined_trade["stop_loss"] = order_buy["sl"] if isLong else order_sell["sl"]
        combined_trade["take_profit"] = order_buy["tp"] if isLong else order_sell["tp"]

        combined_trade["closed_ticket"] = (
            order_sell["ticket"] if isLong else order_buy["ticket"]
        )
        combined_trade["close_order_price"] = (
            order_sell["price_current"] if isLong else order_buy["price_current"]
        )
        combined_trade["close_order_time"] = (
            order_sell["time_done"] if isLong else order_buy["time_done"]
        )
        # Since we have the open/closed ticket... we can get the profit at close, for a historic position
        deals_for_position = mt5.history_deals_get(
            position=combined_trade["position_id"]
        )

        # TODO: convert this to dict
        for deal in deals_for_position:
            if deal[1] == int(combined_trade["closed_ticket"]):
                # TODO: Do we need to also get the commision to set profit?
                print(f"Profit for trade {combined_trade['position_id']}: {deal[13]}")
                combined_trade["profit"] = deal[13]

        # We shouldn't not have a profit in historical trades
        if combined_trade["profit"] is None:
            print(
                f"Profit should not be None for position {combined_trade['position_id']}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Unable to determin profit for {combined_trade['position_id']}. Check adapter logs.",
            )

        list_of_trades.append(combined_trade)

    return list_of_trades


def get_open_trades(accountId: int) -> TradesList:
    trades: TradesList = []

    positions = mt5.positions_get()

    print(positions)

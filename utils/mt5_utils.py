from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import HTTPException
import json
import MetaTrader5 as mt5
import logging

from utils.utils import log_error
from internal_types import TradeRequest, Trade, TradesList

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

log = logging.getLogger(__name__)


def get_trades_for_account(accountId: int) -> TradesList:
    list_of_trades: TradesList = []

    start_time = datetime(2024, 1, 1)
    end_time = datetime.now() + timedelta(
        days=1
    )  # To get around any timezone differences

    # Get all orders
    orders = mt5.history_orders_get(start_time, end_time)
    err = mt5.last_error()
    if orders == None:
        err_str = log_error(
            err, f"/trades/<accountId> [GET] with accountId: {accountId}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to get historic trades: {err_str}"
        )

    log.info(f"Found {len(orders)} orders for account {accountId}")

    position_id_orders = defaultdict(list)

    # Format orders in to a position dict
    for trade in orders:
        trade_dict = trade._asdict()
        position_id_orders[trade_dict["position_id"]].append(trade_dict)

    log.info(f"Found {len(position_id_orders)} individual positions.")

    for position_id, order_list in position_id_orders.items():
        # Build generic trade data
        combined_trade: Trade = {
            "position_id": position_id,
            "symbol": order_list[0]["symbol"],
            "total_volume": order_list[0]["volume_initial"],
        }

        # All trades should have a buy and sell order (eventually)
        order_buy = {}
        order_sell = {}

        for order in order_list:
            log.debug(f"Found order: {json.dumps(order, indent=4)}")
            if (
                order["type"] == 0
            ):  # ORDER_TYPE_BUY https://www.mql5.com/en/docs/constants/tradingconstants/orderproperties#enum_order_type
                log.info(
                    f"For position {position_id} found BUY order with ticket {order.get('ticket')}"
                )
                order_buy = order
            elif (
                order["type"] == 1
            ):  # ORDER_TYPE_SELL https://www.mql5.com/en/docs/constants/tradingconstants/orderproperties#enum_order_type
                order_sell = order
                log.info(
                    f"For position {position_id} found SELL order with ticket {order.get('ticket')}"
                )
            else:
                log.error(f"Unsupport order type for position {position_id}: {order}")

        # Handles the case if an order doesnt have a corresponding close. This means we have found an open trade.
        if order_buy == {} and order_sell == {}:
            log.error(
                f"For position {position_id}, found no order_buy or order_sell -  order_buy: {json.dumps(order_buy, indent=4)}, order_sell: {json.dumps(order_sell, indent=4)}"
            )
        # If there arent at least 2 orders for a position, it must be an open trade.
        elif order_buy == {} or order_sell == {}:
            log.info(
                f"For position {position_id} no {'BUY' if order_buy == {} else 'SELL'} order"
            )
            open_position = mt5.positions_get(
                ticket=order_buy.get("ticket")
                if order_buy
                else order_sell.get("ticket")
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

            # Build the open trades data
            combined_trade["is_open"] = True
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

        combined_trade["close_order_ticket"] = (
            order_sell["ticket"] if isLong else order_buy["ticket"]
        )
        combined_trade["close_order_price"] = (
            order_sell["price_current"] if isLong else order_buy["price_current"]
        )
        combined_trade["close_order_time"] = (
            order_sell["time_done"] if isLong else order_buy["time_done"]
        )

        log.info(
            f"Populated basic order data for position {position_id}: {combined_trade}"
        )

        # Since we have the open/closed ticket... we can get the profit at close, by getting the corresponding deal data
        deals_for_position = mt5.history_deals_get(
            position=combined_trade["position_id"]
        )

        log.info(
            f"Found {len(deals_for_position)} deal(s) for position {position_id} with tickets {[t._asdict().get('ticket') for t in deals_for_position]}"
        )

        for deal in deals_for_position:
            deal_dict = deal._asdict()
            if deal_dict.get("order") == combined_trade["close_order_ticket"]:
                profit = round(
                    deal_dict.get("profit", 0)
                    + deal_dict.get("swap", 0)
                    + deal_dict.get("commission", 0),
                    2,
                )
                print(f"profit is : {profit}")
                print(f"Profit for trade {combined_trade['position_id']}: {profit}")
                combined_trade["profit"] = profit

        # We shouldn't not have a profit in historical trades
        if combined_trade.get("profit") is None:
            print(
                f"Profit should not be None for position {combined_trade['position_id']}"
            )
            raise HTTPException(
                status_code=500,
                detail=f"Unable to calculate profit for position {combined_trade['position_id']}. Check adapter logs.",
            )

        combined_trade["is_open"] = False

        list_of_trades.append(combined_trade)

    return list_of_trades


def get_open_trades(accountId: int) -> TradesList:
    trades: TradesList = []

    positions = mt5.positions_get()

    print(positions)

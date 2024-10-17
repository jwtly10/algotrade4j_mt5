import json
from fastapi import APIRouter, HTTPException
from typing import Dict
import MetaTrader5 as mt5

from utils.mt5_instance import get_mt5_instance
from utils.mt5_utils import get_trades_for_account, build_open_trade_from_position_id
from utils.utils import log_error

from internal_types import TradeRequest, Trade, TradesList

router = APIRouter()


@router.get("/trades/{accountId}", response_model=Dict[str, TradesList])
async def get_trades(accountId: int):
    instance = get_mt5_instance(accountId)
    if not instance:
        raise HTTPException(
            status_code=409,
            detail=f"MT5 instance not initialized for account {accountId}",
        )

    trades: TradesList = get_trades_for_account(accountId)

    if trades != None:
        return {"trades": trades}
    else:
        err_str = log_error(
            error, f"/trades/<accountId> [GET] with accountId: {accountId}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch trades: {err_str}"
        )


@router.post("/trades/{accountId}/open")
async def open_trade(accountId: int, request: TradeRequest):
    instance = get_mt5_instance(accountId)
    if not instance:
        raise HTTPException(
            status_code=409,
            detail=f"MT5 instance not initialized for account {accountId}",
        )

    symbol_info = mt5.symbol_info_tick(request.instrument)
    if not symbol_info:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Instrument/Symbol {request.instrument} for accountId: {accountId}",
        )

    s = mt5.symbol_info(request.instrument)
    if s is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Instrument/Symbol {request.instrument} for accountId: {accountId}",
        )

    s_dict = s._asdict()

    digits = s_dict.get("digits")

    # if the symbol is unavailable in MarketWatch, add it
    if not s.visible:
        print(request.instrument, " is not visible, trying to switch on")
        if not mt5.symbol_select(request.instrument, True):
            raise HTTPException(
                status_code=500,
                detail=f"Symbol {request.instrument} failed to be selected",
            )

    current_price = symbol_info.ask if request.isLong else symbol_info.bid

    stop_loss_pips = abs(request.entryPrice.value - request.stopLoss.value)
    if request.isLong:
        new_stop_loss = current_price - stop_loss_pips
    else:
        new_stop_loss = current_price + stop_loss_pips

    new_take_profit_pips = stop_loss_pips * request.riskRatio
    if request.isLong:
        new_take_profit = current_price + new_take_profit_pips
    else:
        new_take_profit = current_price - new_take_profit_pips

    # TODO: Pip value conversion from Algotrade4j to Adapter
    risk_amount = request.balanceToRisk * request.riskPercentage
    volume = round(risk_amount / (stop_loss_pips * 10), digits)

    order_type = mt5.ORDER_TYPE_BUY if request.isLong else mt5.ORDER_TYPE_SELL
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": request.instrument,
        "volume": volume,
        "type": order_type,
        "price": current_price,
        "sl": new_stop_loss,
        "tp": new_take_profit,
    }

    print(f"Opening trade with req body: {json.dumps(request, indent=4)}")
    result = mt5.order_send(request)
    error = mt5.last_error()

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        # Parse the result id into a 'Trade' type
        res_dict = result._asdict()
        print(f"Result while opening new trade: {json.dumps(res_dict, indent=4)}")

        new_trade = build_open_trade_from_position_id(res_dict.get("order"))

        return new_trade
    else:
        err_str = log_error(
            error,
            f"/trades/open/<accountId> [POST] with accountId: {accountId} and trade req: {request}",
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to open trade: [{result.retcode if result else 'Unknown Error'}] {err_str}",
        )


@router.post("/trades/{accountId}/close/{tradeId}")
async def close_trade(accountId: int, tradeId: int):
    instance = get_mt5_instance(accountId)
    if not instance:
        raise HTTPException(
            status_code=409,
            detail=f"MT5 instance not initialized for account {accountId}",
        )

    position = mt5.positions_get(ticket=tradeId)
    if not position:
        raise HTTPException(status_code=400, detail=f"Open Trade {tradeId} not found")

    symbol = position[0].symbol
    volume = position[0].volume
    position_type = position[0].type  # mt5.ORDER_TYPE_BUY or mt5.ORDER_TYPE_SELL

    close_type = (
        mt5.ORDER_TYPE_SELL
        if position_type == mt5.ORDER_TYPE_BUY
        else mt5.ORDER_TYPE_BUY
    )

    # TODO: Should we have a price deviation?? Its good for manual closes, but would risk order not filling
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": close_type,
        "position": tradeId,
        "deviation": 20,
    }

    result = mt5.order_send(request)

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        res_dict = result._asdict()
        formatted_trade = build_open_trade_from_position_id(res_dict.get("order"))
        return formatted_trade
    else:
        error = mt5.last_error()
        err_str = log_error(
            error,
            f"/trades/close/<accountId> [POST] with accountId: {accountId} and tradeId: {tradeId}",
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to close trade: [{result.retcode if result else 'Unknown Error'}] {err_str}",
        )

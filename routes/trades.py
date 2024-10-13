from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from utils.mt5_instance import get_mt5_instance
import MetaTrader5 as mt5
from utils.utils import log_error

router = APIRouter()


class Number(BaseModel):
    value: float


class TradeRequest(BaseModel):
    instrument: str
    quantity: float
    entryPrice: Number
    stopLoss: Number
    takeProfit: Number
    riskPercentage: float
    riskRatio: float
    balanceToRisk: float
    isLong: bool
    openTime: str


@router.get("/trades/{accountId}")
async def get_trades(accountId: int):
    instance = get_mt5_instance(accountId)
    if not instance:
        raise HTTPException(
            status_code=404,
            detail=f"MT5 instance not initialized for account {accountId}",
        )

    trades = mt5.positions_get()
    error = mt5.last_error()
    if trades:
        return {"status": "success", "trades": [trade._asdict() for trade in trades]}
    else:
        err_str = log_error(
            error, f"/trades/<accountId> [GET] with accountId: {accountId}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch trades: {err_str}"
        )


@router.post("/trades/open/{accountId}")
async def open_trade(accountId: int, req: TradeRequest):
    instance = get_mt5_instance(accountId)
    if not instance:
        raise HTTPException(
            status_code=404,
            detail=f"MT5 instance not initialized for account {accountId}",
        )

    symbol_info = mt5.symbol_info_tick(req.instrument)
    if not symbol_info:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Instrument/Symbol for accountId: {accountId}",
        )

    current_price = symbol_info.ask if req.isLong else symbol_info.bid

    stop_loss_pips = abs(req.entryPrice.value - req.stopLoss.value)
    if req.isLong:
        new_stop_loss = current_price - stop_loss_pips
    else:
        new_stop_loss = current_price + stop_loss_pips

    new_take_profit_pips = stop_loss_pips * req.riskRatio
    if req.isLong:
        new_take_profit = current_price + new_take_profit_pips
    else:
        new_take_profit = current_price - new_take_profit_pips

    # TODO: Pip value conversion from Algotrade4j to Adapter
    risk_amount = req.balanceToRisk * req.riskPercentage
    volume = risk_amount / (stop_loss_pips * 10)

    order_type = mt5.ORDER_TYPE_BUY if req.isLong else mt5.ORDER_TYPE_SELL
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": req.instrument,
        "volume": volume,
        "type": order_type,
        "price": current_price,
        "sl": new_stop_loss,
        "tp": new_take_profit,
    }

    result = mt5.order_send(request)

    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        return result._asdict()
    else:
        error = mt5.last_error()
        err_str = log_error(
            error,
            f"/trades/open/<accountId> [POST] with accountId: {accountId} and trade req: {req}",
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to open trade: [{result.retcode if result else "Unknown Error"}] {err_str}",
        )


@router.post("/trades/close/{accountId}/{tradeId}")
async def close_trade(accountId: int, tradeId: int):
    instance = get_mt5_instance(accountId)
    if not instance:
        raise HTTPException(
            status_code=404,
            detail=f"MT5 instance not initialized for account {accountId}",
        )

    position = mt5.positions_get(ticket=tradeId)
    if not position:
        raise HTTPException(status_code=400, detail=f"Trade {tradeId} not found")

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
        return result._asdict()
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

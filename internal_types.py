from typing import Optional, List
from pydantic import BaseModel


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
    openTime: Optional[float]


class Trade(BaseModel):
    position_id: int
    symbol: str
    total_volume: float
    is_long: bool
    open_order_ticket: int
    open_order_price: float
    open_order_time: int
    stop_loss: float
    take_profit: float
    profit: Optional[float]
    close_order_ticket: Optional[int]
    close_order_price: Optional[float]
    close_order_time: Optional[int]
    is_open: bool


TradesList = List[Trade]

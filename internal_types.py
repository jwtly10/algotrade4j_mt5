from typing import Optional, List
from pydantic import BaseModel


class TradeRequest(BaseModel):
    instrument: str
    quantity: float
    entryPrice: Optional[float]
    stopLoss: Optional[float]
    takeProfit: Optional[float]
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
    profit: Optional[float] = None
    close_order_ticket: Optional[int] = None
    close_order_price: Optional[float] = None
    close_order_time: Optional[int] = None
    is_open: bool


TradesList = List[Trade]

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from mt5_instance import get_mt5_instance
import MetaTrader5 as mt5
from utils import log_error

router = APIRouter()


## TODO
@router.get("/transactions/stream/{accountId}")
async def stream_transactions(accountId: int):
    raise NotImplemented()
    # instance_check = get_mt5_instance(accountId)
    # if instance_check != True:
    #     return instance_check

    # def generate_closed_trades(accountId):
    #     while True:
    #         time.sleep(1)
    #         now = time.time()
    #         closed_trades = mt5.history_deals_get(
    #             datetime.now() - timedelta(seconds=1), datetime.now()
    #         )

    #         if closed_trades:
    #             for trade in closed_trades:
    #                 if trade.ticket not in closed_trades_cache[accountId]:
    #                     closed_trades_cache[accountId][trade.ticket] = now
    #                     yield f"data: {trade._asdict()}\n\n"

    # return Response(generate_closed_trades(accountId), content_type="text/event-stream")

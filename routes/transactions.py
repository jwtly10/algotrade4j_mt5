import json
import asyncio
from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse
from mt5.mt5_instance import get_mt5_instance
from mt5.mt5_utils import get_trades_for_account
from utils.logging import get_logger, log_error

log = get_logger(__name__)


router = APIRouter()

previous_trades_cache = {}

# TODO: Currently if we are running, connect and then disconnect. When we connect again, all close trades since will
# be sent (since the cache persists through connection) temp fix for this will be setting the cache on init, which
# is functionallity similar to Oanda.


@router.get("/transactions/{accountId}/stream")
async def stream_transactions(accountId: int):
    instance_check = get_mt5_instance(accountId)
    if not instance_check:
        raise HTTPException(
            status_code=409,
            detail=f"MT5 instance not initialized for account {accountId}",
        )

    if accountId not in previous_trades_cache:
        previous_trades_cache[accountId] = []

    log.info("New client successfully connected to transaction stream")

    async def generate_closed_trades_events():
        while True:
            current_trades = get_trades_for_account(accountId)
            previous_trades = previous_trades_cache[accountId]
            # To temp fix the above TODO
            previous_trades_cache[accountId] = current_trades

            log.info(
                f"Found {len([t for t in current_trades if t.get('is_open') is True])} open trades"
            )

            # Find new closed trades (trades that were open previously but now closed)
            closed_trades = [
                trade
                for trade in current_trades
                if not trade.get("is_open")  # Trade is now closed
                and any(
                    prev_trade.get("position_id") == trade.get("position_id")
                    and prev_trade.get("is_open")
                    for prev_trade in previous_trades  # Was previously open
                )
            ]


            if closed_trades:
                log.info(
                    f"Found {len(closed_trades)} trades that have closed this iteration"
                )
                for trade in closed_trades:
                    data = {
                        "type": "CLOSE",
                        "position_id": trade.get("position_id"),
                        "profit": trade.get("profit"),
                        "close_order_price": trade.get("close_order_price"),
                    }
                    yield json.dumps(data) + "\n"
            else:
                heartbeat = {"heartbeat": True}
                yield json.dumps(heartbeat) + "\n"

            previous_trades_cache[accountId] = current_trades

            await asyncio.sleep(1)

    return StreamingResponse(
        generate_closed_trades_events(), media_type="text/event-stream"
    )
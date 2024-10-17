import json
import asyncio
from fastapi import APIRouter, HTTPException
from starlette.responses import StreamingResponse
from utils.mt5_instance import get_mt5_instance
from utils.mt5_utils import get_trades_for_account

router = APIRouter()

previous_trades_cache = {}


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

    print("New client successfully connected to transaction stream")

    async def generate_closed_trades_events():
        while True:
            current_trades = get_trades_for_account(accountId)
            previous_trades = previous_trades_cache[accountId]

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

            print(f"Found {len(closed_trades)} open trades")

            if closed_trades:
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
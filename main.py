from fastapi import FastAPI
from routes.account import router as account_router
from routes.trades import router as trades_router
from routes.transactions import router as transactions_router

app = FastAPI()

app.include_router(account_router, prefix="/account")
app.include_router(trades_router, prefix="/trades")
app.include_router(transactions_router, prefix="/trades")


@app.get("/")
async def root():
    return {"message": "Welcome to the Algotrade4j MT5 adapter using FastAPI"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)

from fastapi import FastAPI, Depends, HTTPException, Header
from routes.account import router as account_router
from dotenv import load_dotenv
import os

from routes.trades import router as trades_router
from routes.transactions import router as transactions_router


load_dotenv()

app = FastAPI()

API_KEY = os.getenv("AUTH_API_KEY")
API_KEY_HEADER = "X-API-KEY"


async def api_key_dependency(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Could not validate API KEY")


app.include_router(
    account_router, prefix="/api/v1", dependencies=[Depends(api_key_dependency)]
)
app.include_router(
    trades_router, prefix="/api/v1", dependencies=[Depends(api_key_dependency)]
)
app.include_router(
    transactions_router, prefix="/api/v1", dependencies=[Depends(api_key_dependency)]
)


@app.get("/api/v1/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)

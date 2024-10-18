from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from routes.account import router as account_router
from utils import logging
import os

from routes.trades import router as trades_router
from routes.transactions import router as transactions_router

API_KEY = os.getenv("AUTH_API_KEY")
API_KEY_HEADER = "X-API-KEY"

app = FastAPI(
    title="Algotrade4j MT5 REST Adapter",
    description="REST Adapter for performing broker actions on MT5 Instance from Algotrade4j Trading platform",
    version="0.0.1",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.on_event("startup")
async def startup_event():
    logging.configure_logging()


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)

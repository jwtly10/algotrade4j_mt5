from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from utils.mt5_instance import init_mt5_instance, get_mt5_instance
import utils.validation as validation
from utils.utils import log_error
import MetaTrader5 as mt5

router = APIRouter()

class InitializeRequest(BaseModel):
    accountId: int
    password: str
    server: str
    path: str


@router.post("/initialize")
async def initialize(req: InitializeRequest):
    """
    Initializes a MetaTrader 5 (MT5) account using provided account credentials.
    """

    validation_error = validation.validate_initialise_params(
        req.accountId, req.password, req.server, req.path
    )
    if validation_error:
        raise HTTPException(status_code=400, detail=validation_error)

    print(f"Initializing MT5 Account {req.accountId}")

    success, error = init_mt5_instance(
        req.accountId, req.password, req.server, req.path
    )
    if success:
        print(f"Successfully initialized account %s", req.accountId)
        return {
            "status": "initialized",
            "message": f"Successfully initialized account with id: {req.accountId}",
        }
    else:
        err_str = log_error(
            error, f"/initialize [POST] with accountID: {req.accountId}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize MT5 instance: {err_str}",
        )


@router.get("/accounts/{accountId}")
async def get_account(accountId: int):
    """
    Get account data given MT5 instance accountId
    """

    instance = get_mt5_instance(accountId)
    if not instance:
        raise HTTPException(
            status_code=409,
            detail=f"MT5 instance not initialized for account {accountId}",
        )

    account = mt5.account_info()
    error = mt5.last_error()
    if account:
        return account._asdict()
    else:
        err_str = log_error(
            error, "/accounts/<accountId> [GET] with accountId: {accountId}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch account information: {err_str}"
        )

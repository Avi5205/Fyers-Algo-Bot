import os
from fyers_apiv3 import fyersModel
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


def get_fyers_client() -> fyersModel.FyersModel:
    """
    Returns an authenticated Fyers client using v3 access token.
    You must keep FYERS_ACCESS_TOKEN in .env up to date.
    """
    client_id = os.getenv("FYERS_CLIENT_ID")
    access_token = os.getenv("FYERS_ACCESS_TOKEN")

    if not client_id or not access_token:
        raise RuntimeError("FYERS_CLIENT_ID or FYERS_ACCESS_TOKEN missing in environment/.env")

    fyers = fyersModel.FyersModel(
        client_id=client_id,
        token=access_token,
        log_path="logs"
    )
    logger.info("Created Fyers client")
    return fyers

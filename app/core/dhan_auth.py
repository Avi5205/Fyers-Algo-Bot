import os
import logging
from typing import Optional
from pathlib import Path
from dhanhq import dhanhq, DhanContext
import pandas as pd

logger = logging.getLogger(__name__)

class DhanAuthenticationError(Exception):
    pass

def get_dhan_client() -> dhanhq:
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    
    if not client_id or not access_token:
        missing = []
        if not client_id:
            missing.append("DHAN_CLIENT_ID")
        if not access_token:
            missing.append("DHAN_ACCESS_TOKEN")
        
        raise DhanAuthenticationError(
            f"Missing Dhan credentials: {', '.join(missing)}. "
            "Check that config/credentials.env is properly mounted."
        )
    
    logger.info(f"Initializing Dhan API client for Client ID: {client_id}")
    
    try:
        dhan_context = DhanContext(client_id, access_token)
        client = dhanhq(dhan_context)
        logger.info("✓ Dhan client initialized successfully")
        return client
        
    except Exception as e:
        raise DhanAuthenticationError(f"Failed to initialize Dhan client: {e}")

SECURITY_MASTER_PATH = Path(__file__).parent.parent / "data" / "dhan_security_master.csv"

def get_security_id(symbol: str, exchange: str = "NSE") -> Optional[str]:
    if not SECURITY_MASTER_PATH.exists():
        logger.warning(f"Security master not found: {SECURITY_MASTER_PATH}")
        
        default_map = {
            "RELIANCE": "2885",
            "TCS": "11536",
            "HDFC": "1333",
            "INFY": "1594",
            "ICICIBANK": "4963",
        }
        return default_map.get(symbol.upper())
    
    try:
        df = pd.read_csv(SECURITY_MASTER_PATH, low_memory=False)
        
        match = df[
            (df['SEM_TRADING_SYMBOL'].astype(str).str.upper() == symbol.upper()) &
            (df['SEM_EXM_EXCH_ID'].astype(str).str.upper() == exchange.upper())
        ]
        
        if not match.empty:
            return str(match.iloc[0]['SEM_SMST_SECURITY_ID'])
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to map symbol {symbol}: {e}")
        return None

# core/models.py

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Candle:
    time: datetime
    symbol: str
    exchange: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class Signal:
    time: datetime
    symbol: str
    exchange: str
    side: Side          # BUY / SELL
    strength: float     # 0.0–1.0 confidence
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    metadata: Optional[Dict] = None
    strategy_name: str = ""


@dataclass
class Position:
    symbol: str
    exchange: str
    side: Side
    quantity: int
    entry_price: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    strategy_name: str = ""

    @property
    def direction(self) -> int:
        return 1 if self.side == Side.BUY else -1

    def unrealized_pnl(self, last_price: float) -> float:
        return (last_price - self.entry_price) * self.quantity * self.direction


@dataclass
class Trade:
    time: datetime
    symbol: str
    exchange: str
    side: Side
    quantity: int
    price: float
    strategy_name: str
    pnl: float = 0.0
    is_entry: bool = True

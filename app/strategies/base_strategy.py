# strategies/base_strategy.py

from abc import ABC, abstractmethod
from typing import List, Optional

from loguru import logger

from core.models import Candle, Signal, Position, Trade, Side


class BaseStrategy(ABC):
    """
    BaseStrategy has a single responsibility:
    - Turn a stream of Candle objects into Trades using generated Signals.
    It does not know about DB, broker, or risk engine.
    """

    def __init__(self, name: str, symbol: str, exchange: str = "NSE"):
        self.name = name
        self.symbol = symbol
        self.exchange = exchange
        self.position: Optional[Position] = None
        self.trades: List[Trade] = []

    @abstractmethod
    def generate_signals(self, candle: Candle) -> List[Signal]:
        """Given a new candle, return zero or more trade signals."""
        ...

    def on_candle(self, candle: Candle) -> List[Trade]:
        """Public API: feed candles, get trades (open/close)."""
        if candle.symbol != self.symbol:
            return []

        signals = self.generate_signals(candle)
        new_trades: List[Trade] = []

        for sig in signals:
            sig.strategy_name = self.name
            if sig.side == Side.BUY:
                trades = self._handle_buy_signal(sig, candle)
            else:
                trades = self._handle_sell_signal(sig, candle)
            new_trades.extend(trades)

        return new_trades

    def _handle_buy_signal(self, signal: Signal, candle: Candle) -> List[Trade]:
        trades: List[Trade] = []

        # Already long: ignore
        if self.position and self.position.side == Side.BUY:
            return trades

        # If short, close short
        if self.position and self.position.side == Side.SELL:
            close_trade = self._close_position(candle)
            trades.append(close_trade)

        qty = self._position_size(candle)
        entry_price = candle.close

        self.position = Position(
            symbol=self.symbol,
            exchange=self.exchange,
            side=Side.BUY,
            quantity=qty,
            entry_price=entry_price,
            entry_time=candle.time,
            stop_loss=signal.stop_loss,
            target=signal.target,
            strategy_name=self.name,
        )

        trade = Trade(
            time=candle.time,
            symbol=self.symbol,
            exchange=self.exchange,
            side=Side.BUY,
            quantity=qty,
            price=entry_price,
            strategy_name=self.name,
            is_entry=True,
            pnl=0.0,
        )
        self.trades.append(trade)
        trades.append(trade)

        logger.debug(f"[{self.name}] Open LONG {qty} {self.symbol} @ {entry_price}")
        return trades

    def _handle_sell_signal(self, signal: Signal, candle: Candle) -> List[Trade]:
        trades: List[Trade] = []

        # Already short: ignore
        if self.position and self.position.side == Side.SELL:
            return trades

        # If long, close long
        if self.position and self.position.side == Side.BUY:
            close_trade = self._close_position(candle)
            trades.append(close_trade)

        qty = self._position_size(candle)
        entry_price = candle.close

        self.position = Position(
            symbol=self.symbol,
            exchange=self.exchange,
            side=Side.SELL,
            quantity=qty,
            entry_price=entry_price,
            entry_time=candle.time,
            stop_loss=signal.stop_loss,
            target=signal.target,
            strategy_name=self.name,
        )

        trade = Trade(
            time=candle.time,
            symbol=self.symbol,
            exchange=self.exchange,
            side=Side.SELL,
            quantity=qty,
            price=entry_price,
            strategy_name=self.name,
            is_entry=True,
            pnl=0.0,
        )
        self.trades.append(trade)
        trades.append(trade)

        logger.debug(f"[{self.name}] Open SHORT {qty} {self.symbol} @ {entry_price}")
        return trades

    def _close_position(self, candle: Candle) -> Trade:
        assert self.position is not None
        exit_price = candle.close
        pnl = self.position.unrealized_pnl(exit_price)
        side = Side.SELL if self.position.side == Side.BUY else Side.BUY

        trade = Trade(
            time=candle.time,
            symbol=self.symbol,
            exchange=self.exchange,
            side=side,
            quantity=self.position.quantity,
            price=exit_price,
            strategy_name=self.name,
            is_entry=False,
            pnl=pnl,
        )
        logger.debug(
            f"[{self.name}] Close {self.position.side.value} {self.position.quantity} "
            f"{self.symbol} @ {exit_price}, PnL={pnl:.2f}"
        )

        self.position = None
        self.trades.append(trade)
        return trade

    def _position_size(self, candle: Candle) -> int:
        """Single responsibility: simple position sizing; extended later for risk-based sizing."""
        return 1

    def finalize(self, last_candle: Candle) -> List[Trade]:
        """Close any open position at end of backtest."""
        if self.position:
            return [self._close_position(last_candle)]
        return []

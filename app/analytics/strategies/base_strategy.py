from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from loguru import logger


class BaseStrategy(ABC):
    """
    Base class for all trading strategies
    """
    
    def __init__(self, symbol: str, name: str = "base_strategy"):
        self.symbol = symbol
        self.name = name
        self.position: Optional[Dict[str, Any]] = None
        self.trades = []
        
    @abstractmethod
    async def generate_signals(self, candles):
        """
        Generate trading signals from historical candles
        Must be implemented by subclasses
        """
        pass
    
    async def on_candle(self, candle: Dict[str, Any]):
        """
        Process incoming candle (event-driven)
        Candle is a dict with keys: time, symbol, open, high, low, close, volume
        """
        # Validate candle belongs to this strategy's symbol
        if candle.get('symbol') != self.symbol:
            return
        
        # Subclasses should override this or use generate_signals
        pass
    
    def _calculate_ema(self, values, period):
        """Calculate Exponential Moving Average"""
        if len(values) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = sum(values[:period]) / period
        
        for value in values[period:]:
            ema = (value - ema) * multiplier + ema
        
        return ema
    
    def _calculate_sma(self, values, period):
        """Calculate Simple Moving Average"""
        if len(values) < period:
            return None
        return sum(values[-period:]) / period
    
    async def _handle_buy_signal(self, candle: Dict[str, Any], quantity: int = 1):
        """Handle BUY signal"""
        if self.position:
            # Already in position
            if self.position['side'] == 'SELL':
                # Close SHORT position first
                await self._close_position(candle)
            else:
                # Already LONG
                return
        
        # Open LONG position
        self.position = {
            'side': 'BUY',
            'entry_price': candle['close'],
            'quantity': quantity,
            'entry_time': candle['time'],
        }
        
        logger.debug(
            f"[{self.name}] Open LONG {quantity} {self.symbol} @ {candle['close']}"
        )
    
    async def _handle_sell_signal(self, candle: Dict[str, Any], quantity: int = 1):
        """Handle SELL signal"""
        if self.position:
            # Already in position
            if self.position['side'] == 'BUY':
                # Close LONG position first
                await self._close_position(candle)
            else:
                # Already SHORT
                return
        
        # Open SHORT position
        self.position = {
            'side': 'SELL',
            'entry_price': candle['close'],
            'quantity': quantity,
            'entry_time': candle['time'],
        }
        
        logger.debug(
            f"[{self.name}] Open SHORT {quantity} {self.symbol} @ {candle['close']}"
        )
    
    async def _close_position(self, candle: Dict[str, Any]):
        """Close current position"""
        if not self.position:
            return
        
        exit_price = candle['close']
        entry_price = self.position['entry_price']
        quantity = self.position['quantity']
        side = self.position['side']
        
        # Calculate PnL
        if side == 'BUY':
            pnl = (exit_price - entry_price) * quantity
        else:  # SELL
            pnl = (entry_price - exit_price) * quantity
        
        # Record trade
        trade = {
            'symbol': self.symbol,
            'side': side,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'quantity': quantity,
            'pnl': pnl,
            'entry_time': self.position['entry_time'],
            'exit_time': candle['time'],
        }
        
        self.trades.append(trade)
        
        logger.debug(
            f"[{self.name}] Close {side} {quantity} {self.symbol} @ {exit_price}, "
            f"PnL={pnl:.2f}"
        )
        
        # Clear position
        self.position = None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get trading statistics"""
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
            }
        
        total_trades = len(self.trades)
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] < 0]
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
        }

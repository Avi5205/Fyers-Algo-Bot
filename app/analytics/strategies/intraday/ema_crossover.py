from analytics.strategies.base_strategy import BaseStrategy
from loguru import logger


class EmaCrossoverStrategy(BaseStrategy):
    """
    Simple EMA crossover strategy
    - Buy when fast EMA crosses above slow EMA
    - Sell when fast EMA crosses below slow EMA
    """
    
    def __init__(self, symbol: str, fast_period: int = 9, slow_period: int = 21):
        super().__init__(symbol=symbol, name="ema_crossover")
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.price_history = []
        self.prev_fast_ema = None
        self.prev_slow_ema = None
        
    async def generate_signals(self, candles):
        """Generate signals from candle data"""
        signals = []
        for candle in candles:
            signal = await self.on_candle(candle)
            if signal:
                signals.append(signal)
        return signals
    
    async def on_candle(self, candle):
        """Process each candle"""
        close = candle['close']
        
        # Build price history
        self.price_history.append(close)
        
        # Keep only necessary history
        max_period = max(self.fast_period, self.slow_period)
        if len(self.price_history) > max_period * 3:
            self.price_history = self.price_history[-max_period * 3:]
        
        # Calculate EMAs
        fast_ema = self._calculate_ema(self.price_history, self.fast_period)
        slow_ema = self._calculate_ema(self.price_history, self.slow_period)
        
        if fast_ema is None or slow_ema is None:
            return None
        
        # Detect crossover
        if self.prev_fast_ema and self.prev_slow_ema:
            # Bullish crossover: fast crosses above slow
            if self.prev_fast_ema <= self.prev_slow_ema and fast_ema > slow_ema:
                await self._handle_buy_signal(candle, quantity=1)
                self.prev_fast_ema = fast_ema
                self.prev_slow_ema = slow_ema
                return {'action': 'BUY', 'price': close}
            
            # Bearish crossover: fast crosses below slow
            elif self.prev_fast_ema >= self.prev_slow_ema and fast_ema < slow_ema:
                await self._handle_sell_signal(candle, quantity=1)
                self.prev_fast_ema = fast_ema
                self.prev_slow_ema = slow_ema
                return {'action': 'SELL', 'price': close}
        
        # Update previous values
        self.prev_fast_ema = fast_ema
        self.prev_slow_ema = slow_ema
        
        return None

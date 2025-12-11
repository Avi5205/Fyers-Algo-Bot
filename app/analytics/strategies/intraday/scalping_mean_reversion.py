from analytics.strategies.base_strategy import BaseStrategy
from loguru import logger


class ScalpingMeanReversionStrategy(BaseStrategy):
    """
    Scalping strategy using Bollinger Bands mean reversion
    - Buy: Price touches lower band
    - Sell: Price touches upper band or middle band
    """
    
    def __init__(self, symbol: str, bb_period: int = 20, bb_std: float = 2.0):
        super().__init__(symbol, "scalping_mean_reversion")
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.price_history = []
        
    def calculate_bollinger_bands(self, prices):
        """Calculate Bollinger Bands"""
        if len(prices) < self.bb_period:
            return None, None, None
        
        recent = prices[-self.bb_period:]
        ma = sum(recent) / len(recent)
        
        variance = sum((x - ma) ** 2 for x in recent) / len(recent)
        std = variance ** 0.5
        
        upper = ma + (self.bb_std * std)
        lower = ma - (self.bb_std * std)
        
        return upper, ma, lower
    
    async def generate_signals(self, candles):
        """Generate signals from candle data (required by BaseStrategy)"""
        signals = []
        for candle in candles:
            signal = await self.on_candle(candle)
            if signal:
                signals.append(signal)
        return signals
    
    async def on_candle(self, candle):
        """Process each candle"""
        close = candle["close"]
        
        # Store price history
        self.price_history.append(close)
        
        if len(self.price_history) > 100:
            self.price_history = self.price_history[-100:]
        
        # Calculate Bollinger Bands
        upper, middle, lower = self.calculate_bollinger_bands(self.price_history)
        
        if not upper:
            return None
        
        # Trading logic
        if not self.position:
            # Buy at lower band (oversold)
            if close <= lower:
                await self._handle_buy_signal(candle, quantity=1)
                return {'action': 'BUY', 'price': close, 'upper': upper, 'middle': middle, 'lower': lower}
        else:
            # Sell at upper band or middle (profit taking)
            if close >= upper or close >= middle:
                await self._handle_sell_signal(candle)
                return {'action': 'SELL', 'price': close, 'upper': upper, 'middle': middle, 'lower': lower}
        
        return None

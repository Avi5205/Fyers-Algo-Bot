from analytics.strategies.base_strategy import BaseStrategy
from loguru import logger


class SwingTrendStrategy(BaseStrategy):
    """
    Swing trading strategy using RSI + Moving Average
    - Buy: RSI < 30 and price > MA50
    - Sell: RSI > 70 or price < MA50
    """
    
    def __init__(self, symbol: str, rsi_period: int = 14, ma_period: int = 50):
        super().__init__(symbol, "swing_trend")
        self.rsi_period = rsi_period
        self.ma_period = ma_period
        self.price_history = []
        
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        if len(prices) < period + 1:
            return 50
        
        gains = []
        losses = []
        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_ma(self, prices, period):
        """Calculate Moving Average"""
        if len(prices) < period:
            return prices[-1] if prices else 0
        return sum(prices[-period:]) / period
    
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
        
        # Keep only last 200 candles for performance
        if len(self.price_history) > 200:
            self.price_history = self.price_history[-200:]
        
        # Calculate indicators
        rsi = self.calculate_rsi(self.price_history, self.rsi_period)
        ma = self.calculate_ma(self.price_history, self.ma_period)
        
        # Trading logic
        if not self.position:
            # Buy signal: RSI oversold + price above MA
            if rsi < 30 and close > ma:
                await self._handle_buy_signal(candle, quantity=1)
                return {'action': 'BUY', 'price': close, 'rsi': rsi, 'ma': ma}
        else:
            # Sell signal: RSI overbought OR price below MA
            if rsi > 70 or close < ma:
                await self._handle_sell_signal(candle)
                return {'action': 'SELL', 'price': close, 'rsi': rsi, 'ma': ma}
        
        return None

from loguru import logger


class RiskManager:
    """
    Risk management module for position sizing, stop-loss, and risk limits
    """
    
    def __init__(self, 
                 initial_capital: float = 100000.0,
                 max_risk_per_trade: float = 0.02,  # 2% per trade
                 max_portfolio_risk: float = 0.06,   # 6% total
                 stop_loss_pct: float = 0.02,        # 2% stop loss
                 take_profit_pct: float = 0.04):     # 4% take profit
        
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_risk_per_trade = max_risk_per_trade
        self.max_portfolio_risk = max_portfolio_risk
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        self.open_positions = {}
        self.closed_trades = []
        
    def calculate_position_size(self, entry_price: float) -> int:
        """
        Calculate safe position size based on risk parameters
        Returns: quantity to buy
        """
        risk_amount = self.current_capital * self.max_risk_per_trade
        stop_loss_distance = entry_price * self.stop_loss_pct
        
        if stop_loss_distance == 0:
            return 1
        
        quantity = int(risk_amount / stop_loss_distance)
        
        # Minimum 1 share
        return max(1, quantity)
    
    def calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """Calculate stop loss price"""
        if side == "BUY":
            return entry_price * (1 - self.stop_loss_pct)
        else:  # SHORT
            return entry_price * (1 + self.stop_loss_pct)
    
    def calculate_take_profit(self, entry_price: float, side: str) -> float:
        """Calculate take profit price"""
        if side == "BUY":
            return entry_price * (1 + self.take_profit_pct)
        else:  # SHORT
            return entry_price * (1 - self.take_profit_pct)
    
    def check_stop_loss(self, symbol: str, current_price: float) -> bool:
        """Check if stop loss is hit"""
        if symbol not in self.open_positions:
            return False
        
        pos = self.open_positions[symbol]
        stop_loss = pos['stop_loss']
        
        if pos['side'] == "BUY":
            return current_price <= stop_loss
        else:  # SHORT
            return current_price >= stop_loss
    
    def check_take_profit(self, symbol: str, current_price: float) -> bool:
        """Check if take profit is hit"""
        if symbol not in self.open_positions:
            return False
        
        pos = self.open_positions[symbol]
        take_profit = pos['take_profit']
        
        if pos['side'] == "BUY":
            return current_price >= take_profit
        else:  # SHORT
            return current_price <= take_profit
    
    def open_position(self, symbol: str, side: str, entry_price: float, quantity: int):
        """Record new position"""
        stop_loss = self.calculate_stop_loss(entry_price, side)
        take_profit = self.calculate_take_profit(entry_price, side)
        
        self.open_positions[symbol] = {
            'side': side,
            'entry_price': entry_price,
            'quantity': quantity,
            'stop_loss': stop_loss,
            'take_profit': take_profit
        }
        
        logger.info(f"[RiskMgr] Opened {side} {quantity} {symbol} @ ₹{entry_price:.2f} | "
                   f"SL: ₹{stop_loss:.2f} | TP: ₹{take_profit:.2f}")
    
    def close_position(self, symbol: str, exit_price: float) -> dict:
        """Close position and calculate PnL"""
        if symbol not in self.open_positions:
            return None
        
        pos = self.open_positions.pop(symbol)
        
        if pos['side'] == "BUY":
            pnl = (exit_price - pos['entry_price']) * pos['quantity']
        else:  # SHORT
            pnl = (pos['entry_price'] - exit_price) * pos['quantity']
        
        self.current_capital += pnl
        
        trade = {
            'symbol': symbol,
            'side': pos['side'],
            'entry': pos['entry_price'],
            'exit': exit_price,
            'quantity': pos['quantity'],
            'pnl': pnl
        }
        
        self.closed_trades.append(trade)
        
        logger.info(f"[RiskMgr] Closed {pos['side']} {pos['quantity']} {symbol} @ ₹{exit_price:.2f} | "
                   f"PnL: ₹{pnl:.2f} | Capital: ₹{self.current_capital:.2f}")
        
        return trade
    
    def get_portfolio_risk(self) -> float:
        """Calculate current portfolio risk exposure"""
        if not self.open_positions:
            return 0.0
        
        total_risk = len(self.open_positions) * self.max_risk_per_trade
        return total_risk
    
    def can_open_position(self) -> bool:
        """Check if new position can be opened (risk limits)"""
        current_risk = self.get_portfolio_risk()
        new_risk = current_risk + self.max_risk_per_trade
        
        return new_risk <= self.max_portfolio_risk
    
    def get_stats(self) -> dict:
        """Get trading statistics"""
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0
            }
        
        total = len(self.closed_trades)
        wins = [t for t in self.closed_trades if t['pnl'] > 0]
        losses = [t for t in self.closed_trades if t['pnl'] < 0]
        
        total_pnl = sum(t['pnl'] for t in self.closed_trades)
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
        
        gross_profit = sum(t['pnl'] for t in wins)
        gross_loss = abs(sum(t['pnl'] for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        return {
            'total_trades': total,
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': (len(wins) / total * 100) if total > 0 else 0,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'final_capital': self.current_capital
        }

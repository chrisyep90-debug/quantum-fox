import asyncio
import schedule
import time
import logging
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import APIError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ============================================================================
# LOGGING SETUP
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
ALPACA_ENV = os.getenv("ALPACA_ENV", "live").lower()

# Trading parameters
MAX_DAILY_TRADES = 30
TOP_N_STOCKS = 3
TARGET_STOCKS = ["AAPL", "MSFT", "TSLA", "NVDA", "GOOGL", "AMZN", "META", "NFLX", "AMD", "PYPL"]
POSITION_SIZE = 0.05  # 5% of portfolio per trade
PROFIT_TARGET_PCT = 0.5  # 0.5% profit target per trade
STOP_LOSS_PCT = 0.3  # 0.3% stop loss

# ============================================================================
# ALPACA API CLIENT
# ============================================================================
class TradingClient:
    def __init__(self):
        endpoint = "https://api.alpaca.markets"
        self.api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, base_url=endpoint, api_version='v2')
        self.trades_today = 0
        logger.info("🦊 Trading Client Initialized")
    
    def get_account(self):
        """Get account info"""
        return self.api.get_account()
    
    def get_positions(self):
        """Get all open positions"""
        return self.api.list_positions()
    
    def get_orders(self):
        """Get all open orders"""
        return self.api.list_orders(status='open')
    
    def execute_buy(self, symbol, qty, limit_price=None):
        """Execute buy order"""
        try:
            if limit_price:
                order = self.api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='buy',
                    type='limit',
                    time_in_force='ioc',
                    limit_price=limit_price
                )
            else:
                order = self.api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='buy',
                    type='market',
                    time_in_force='ioc'
                )
            
            self.trades_today += 1
            logger.info(f"✅ BUY: {symbol} x{qty} @ ${limit_price:.2f if limit_price else 'market'} | ID: {order.id}")
            return order
        
        except APIError as e:
            logger.error(f"❌ BUY FAILED ({symbol}): {e}")
            return None
    
    def execute_sell(self, symbol, qty, limit_price=None):
        """Execute sell order"""
        try:
            if limit_price:
                order = self.api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='sell',
                    type='limit',
                    time_in_force='ioc',
                    limit_price=limit_price
                )
            else:
                order = self.api.submit_order(
                    symbol=symbol,
                    qty=qty,
                    side='sell',
                    type='market',
                    time_in_force='ioc'
                )
            
            self.trades_today += 1
            logger.info(f"✅ SELL: {symbol} x{qty} @ ${limit_price:.2f if limit_price else 'market'} | ID: {order.id}")
            return order
        
        except APIError as e:
            logger.error(f"❌ SELL FAILED ({symbol}): {e}")
            return None
    
    def close_position(self, symbol):
        """Close position in a symbol"""
        try:
            self.api.close_position(symbol)
            logger.info(f"🔒 Position closed: {symbol}")
            return True
        except APIError as e:
            logger.error(f"❌ CLOSE POSITION FAILED ({symbol}): {e}")
            return False

# ============================================================================
# AI PREDICTION ENGINE
# ============================================================================
class AIPredictor:
    """AI-powered stock prediction engine"""
    
    @staticmethod
    def calculate_indicators(data):
        """Calculate technical indicators for prediction"""
        df = data.copy()
        
        # Moving Averages
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['SMA_50'] = df['Close'].rolling(50).mean()
        df['SMA_200'] = df['Close'].rolling(200).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
        
        # Bollinger Bands
        df['BB_SMA'] = df['Close'].rolling(20).mean()
        df['BB_STD'] = df['Close'].rolling(20).std()
        df['BB_Upper'] = df['BB_SMA'] + (df['BB_STD'] * 2)
        df['BB_Lower'] = df['BB_SMA'] - (df['BB_STD'] * 2)
        
        # ATR (Volatility)
        df['TR'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift()),
                abs(df['Low'] - df['Close'].shift())
            )
        )
        df['ATR'] = df['TR'].rolling(14).mean()
        
        # Volume trend
        df['Volume_SMA'] = df['Volume'].rolling(20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
        
        return df.dropna()
    
    @staticmethod
    def predict_next_move(symbol, intraday_data, daily_data):
        """
        Predict next intraday move (BUY/SELL/HOLD)
        Uses ML-like scoring based on multiple indicators
        """
        try:
            # Calculate indicators
            intraday = AIPredictor.calculate_indicators(intraday_data)
            daily = AIPredictor.calculate_indicators(daily_data)
            
            if len(intraday) < 2 or len(daily) < 2:
                return {'action': 'HOLD', 'confidence': 0, 'reason': 'Insufficient data'}
            
            # Get latest values
            latest_intraday = intraday.iloc[-1]
            latest_daily = daily.iloc[-1]
            
            score = 0
            reasons = []
            
            # === MOMENTUM SIGNALS ===
            # SMA crossover (20 > 50 = bullish)
            if latest_daily['SMA_20'] > latest_daily['SMA_50']:
                score += 2
                reasons.append("SMA20 > SMA50 (Bullish)")
            elif latest_daily['SMA_20'] < latest_daily['SMA_50']:
                score -= 2
                reasons.append("SMA20 < SMA50 (Bearish)")
            
            # Trend confirmation (50 > 200)
            if latest_daily['SMA_50'] > latest_daily['SMA_200']:
                score += 1.5
                reasons.append("Uptrend (50 > 200)")
            elif latest_daily['SMA_50'] < latest_daily['SMA_200']:
                score -= 1.5
                reasons.append("Downtrend (50 < 200)")
            
            # === RSI SIGNALS ===
            rsi = latest_intraday['RSI']
            if rsi < 30:
                score += 2
                reasons.append("RSI Oversold (Bullish)")
            elif rsi > 70:
                score -= 2
                reasons.append("RSI Overbought (Bearish)")
            elif 40 < rsi < 60:
                score += 0.5
                reasons.append("RSI Neutral")
            
            # === MACD SIGNALS ===
            if latest_intraday['MACD'] > latest_intraday['MACD_Signal']:
                score += 1.5
                reasons.append("MACD Bullish Crossover")
            else:
                score -= 1.5
                reasons.append("MACD Bearish Crossover")
            
            if latest_intraday['MACD_Hist'] > 0 and latest_intraday['MACD_Hist'] > latest_intraday['MACD_Hist']:
                score += 1
                reasons.append("MACD Momentum Increasing")
            
            # === BOLLINGER BAND SIGNALS ===
            close = latest_intraday['Close']
            if close < latest_intraday['BB_Lower']:
                score += 1.5
                reasons.append("Price Below BB Lower (Reversal Buy)")
            elif close > latest_intraday['BB_Upper']:
                score -= 1.5
                reasons.append("Price Above BB Upper (Reversal Sell)")
            
            # === VOLUME SIGNALS ===
            if latest_intraday['Volume_Ratio'] > 1.5:
                if score > 0:
                    score += 1
                    reasons.append("High Volume Confirms Bullish")
                else:
                    score -= 1
                    reasons.append("High Volume Confirms Bearish")
            
            # === VOLATILITY ADJUSTMENT ===
            atr_percent = (latest_intraday['ATR'] / close) * 100
            if atr_percent > 2:
                score *= 0.8  # Reduce confidence in high volatility
                reasons.append("High Volatility - Caution")
            
            # === DETERMINE ACTION ===
            confidence = min(abs(score) / 10 * 100, 100)
            
            if score > 2:
                action = 'BUY'
            elif score < -2:
                action = 'SELL'
            else:
                action = 'HOLD'
            
            return {
                'symbol': symbol,
                'action': action,
                'confidence': round(confidence, 2),
                'score': round(score, 2),
                'reasons': reasons,
                'rsi': round(rsi, 2),
                'macd': round(latest_intraday['MACD'], 4),
                'sma_20': round(latest_daily['SMA_20'], 2),
                'sma_50': round(latest_daily['SMA_50'], 2)
            }
        
        except Exception as e:
            logger.error(f"Prediction error for {symbol}: {e}")
            return {'action': 'HOLD', 'confidence': 0, 'reason': str(e)}

# ============================================================================
# TRADING BOT
# ============================================================================
class QuantumFoxBot:
    """Autonomous AI Trading Bot"""
    
    def __init__(self):
        self.client = TradingClient()
        self.predictor = AIPredictor()
        self.selected_stocks = []
        self.daily_predictions = {}
        logger.info("🦊 Quantum Fox Bot Initialized")
    
    def select_top_stocks(self):
        """Select top 3 stocks to trade for the day"""
        logger.info("📊 Analyzing top stocks...")
        
        scores = {}
        
        for stock in TARGET_STOCKS:
            try:
                # Get data
                daily_data = yf.download(stock, period="6mo", interval="1d", progress=False)
                intraday_data = yf.download(stock, period="5d", interval="1h", progress=False)
                
                if daily_data.empty or intraday_data.empty:
                    continue
                
                # Predict
                prediction = self.predictor.predict_next_move(stock, intraday_data, daily_data)
                
                # Score based on confidence and action
                score = prediction['confidence']
                if prediction['action'] == 'BUY':
                    score *= 1.2
                elif prediction['action'] == 'SELL':
                    score *= 0.8
                
                scores[stock] = {
                    'score': score,
                    'prediction': prediction
                }
                
                logger.info(f"  {stock}: {prediction['action']} (Confidence: {prediction['confidence']}%)")
            
            except Exception as e:
                logger.error(f"Error analyzing {stock}: {e}")
                continue
        
        # Select top 3
        if not scores:
            logger.warning("No stocks analyzed successfully")
            return []
        
        top_3 = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)[:TOP_N_STOCKS]
        self.selected_stocks = [stock[0] for stock in top_3]
        self.daily_predictions = {stock[0]: stock[1]['prediction'] for stock in top_3}
        
        logger.info(f"✅ Selected Top 3 Stocks: {self.selected_stocks}")
        
        for stock in self.selected_stocks:
            pred = self.daily_predictions[stock]
            logger.info(f"  {stock}: {pred['action']} (Conf: {pred['confidence']}%) - {', '.join(pred['reasons'][:2])}")
        
        return self.selected_stocks
    
    def execute_trading_cycle(self):
        """Execute one complete trading cycle"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 TRADING CYCLE START - {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"{'='*60}")
        
        if not self.selected_stocks:
            logger.warning("No stocks selected. Run select_top_stocks first.")
            return
        
        try:
            account = self.client.get_account()
            portfolio_value = float(account.equity)
            position_value = portfolio_value * POSITION_SIZE
            
            logger.info(f"💰 Portfolio: ${portfolio_value:,.2f} | Position Size: ${position_value:,.2f}")
            logger.info(f"📊 Trades Today: {self.client.trades_today}/{MAX_DAILY_TRADES}")
            
            if self.client.trades_today >= MAX_DAILY_TRADES:
                logger.warning("❌ Daily trade limit reached!")
                return
            
            # Process each selected stock
            for stock in self.selected_stocks:
                if self.client.trades_today >= MAX_DAILY_TRADES:
                    break
                
                try:
                    # Get real-time data
                    intraday = yf.download(stock, period="1d", interval="1m", progress=False)
                    daily = yf.download(stock, period="6mo", interval="1d", progress=False)
                    
                    if intraday.empty or daily.empty:
                        continue
                    
                    # Get latest prediction
                    prediction = self.predictor.predict_next_move(stock, intraday, daily)
                    current_price = intraday['Close'].iloc[-1]
                    
                    logger.info(f"\n📈 {stock} @ ${current_price:.2f}")
                    logger.info(f"  Action: {prediction['action']} | Confidence: {prediction['confidence']}%")
                    
                    # Check for existing position
                    positions = self.client.get_positions()
                    stock_position = next((p for p in positions if p.symbol == stock), None)
                    
                    if prediction['action'] == 'BUY' and prediction['confidence'] > 60:
                        # Calculate quantity
                        qty = int(position_value / current_price)
                        
                        if qty > 0:
                            # Set limit price slightly below market for better fills
                            limit_price = current_price * 0.9995
                            self.client.execute_buy(stock, qty, limit_price)
                    
                    elif prediction['action'] == 'SELL' and stock_position:
                        # Sell at profit target or stop loss
                        qty = int(float(stock_position.qty))
                        entry_price = float(stock_position.avg_entry_price)
                        
                        profit_target = entry_price * (1 + PROFIT_TARGET_PCT / 100)
                        stop_loss = entry_price * (1 - STOP_LOSS_PCT / 100)
                        
                        if current_price >= profit_target:
                            logger.info(f"  📊 Profit target hit! ({current_price:.2f} >= {profit_target:.2f})")
                            self.client.execute_sell(stock, qty, current_price * 1.0005)
                        elif current_price <= stop_loss:
                            logger.warning(f"  🛑 Stop loss hit! ({current_price:.2f} <= {stop_loss:.2f})")
                            self.client.execute_sell(stock, qty)
                        elif prediction['confidence'] > 70:
                            self.client.execute_sell(stock, qty, current_price * 1.0005)
                
                except Exception as e:
                    logger.error(f"Error trading {stock}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Trading cycle error: {e}")
        
        logger.info(f"{'='*60}")
        logger.info(f"✅ TRADING CYCLE END - Trades: {self.client.trades_today}")
        logger.info(f"{'='*60}\n")
    
    def scheduled_nightly_analysis(self):
        """Run nightly stock selection (21:00 ET)"""
        logger.info("\n🌙 NIGHTLY ANALYSIS")
        self.select_top_stocks()
    
    def scheduled_intraday_trading(self):
        """Run intraday trading during market hours"""
        # Market hours: 9:30 AM - 4:00 PM ET
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        # Check if market is open (9:30 AM - 4:00 PM ET)
        if 9 <= hour < 16 and (hour != 9 or minute >= 30):
            self.execute_trading_cycle()
    
    def start_scheduler(self):
        """Start the trading scheduler"""
        logger.info("📅 Starting Trading Scheduler...")
        
        # Nightly analysis at 9:00 PM ET (analyze for next day)
        schedule.every().day.at("21:00").do(self.scheduled_nightly_analysis)
        
        # Intraday trading every 15 minutes during market hours
        schedule.every(15).minutes.do(self.scheduled_intraday_trading)
        
        logger.info("✅ Scheduler Started")
        logger.info("  - Nightly analysis: 9:00 PM ET")
        logger.info("  - Intraday trading: Every 15 minutes (9:30 AM - 4:00 PM ET)")
        
        # Run scheduler
        while True:
            schedule.run_pending()
            time.sleep(60)

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    logger.info("\n" + "="*60)
    logger.info("🦊 QUANTUM FOX - AUTONOMOUS AI TRADING BOT")
    logger.info("="*60)
    logger.info(f"Mode: LIVE TRADING")
    logger.info(f"Top Stocks: {TOP_N_STOCKS}")
    logger.info(f"Max Trades/Day: {MAX_DAILY_TRADES}")
    logger.info(f"Position Size: {POSITION_SIZE*100}% of portfolio")
    logger.info(f"Profit Target: {PROFIT_TARGET_PCT}%")
    logger.info(f"Stop Loss: {STOP_LOSS_PCT}%")
    logger.info("="*60 + "\n")
    
    try:
        bot = QuantumFoxBot()
        bot.start_scheduler()
    except KeyboardInterrupt:
        logger.info("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

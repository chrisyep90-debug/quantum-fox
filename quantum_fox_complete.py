# ============================================================================
# QUANTUM FOX 🦊 - COMPLETE AUTONOMOUS AI TRADING BOT
# ============================================================================
# One Complete Script - Copy & Paste Ready
# Features:
# - Autonomous trading (30 trades/day)
# - AI-powered stock selection (top 3 daily)
# - Buy low, sell high strategy
# - Real-time monitoring
# - Live Alpaca integration
# ============================================================================

import asyncio
import schedule
import time
import logging
import sys
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
# CONFIGURATION
# ============================================================================
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "your_api_key")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "your_secret_key")

# Trading parameters
MAX_DAILY_TRADES = 30
TOP_N_STOCKS = 3
TARGET_STOCKS = ["AAPL", "MSFT", "TSLA", "NVDA", "GOOGL", "AMZN", "META", "NFLX", "AMD", "PYPL"]
POSITION_SIZE = 0.05  # 5% of portfolio per trade
PROFIT_TARGET_PCT = 0.5  # 0.5% profit target
STOP_LOSS_PCT = 0.3  # 0.3% stop loss

# ============================================================================
# LOGGING
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('quantum_fox.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# TRADING CLIENT
# ============================================================================
class TradingClient:
    """Alpaca Trading API Client"""
    
    def __init__(self, api_key, secret_key):
        try:
            self.api = tradeapi.REST(api_key, secret_key, base_url="https://api.alpaca.markets", api_version='v2')
            self.trades_today = 0
            logger.info("✅ Trading Client Connected")
        except Exception as e:
            logger.error(f"❌ Client Error: {e}")
            self.api = None
    
    def get_account(self):
        """Get account information"""
        try:
            return self.api.get_account()
        except Exception as e:
            logger.error(f"Account error: {e}")
            return None
    
    def get_positions(self):
        """Get all open positions"""
        try:
            return self.api.list_positions()
        except Exception as e:
            logger.error(f"Positions error: {e}")
            return []
    
    def execute_buy(self, symbol, qty, limit_price=None):
        """Execute buy order"""
        try:
            if limit_price:
                order = self.api.submit_order(
                    symbol=symbol, qty=qty, side='buy',
                    type='limit', time_in_force='ioc', limit_price=limit_price
                )
            else:
                order = self.api.submit_order(
                    symbol=symbol, qty=qty, side='buy',
                    type='market', time_in_force='ioc'
                )
            
            self.trades_today += 1
            logger.info(f"✅ BUY: {symbol} x{qty} | ID: {order.id}")
            return order
        except APIError as e:
            logger.error(f"❌ BUY FAILED ({symbol}): {e}")
            return None
    
    def execute_sell(self, symbol, qty, limit_price=None):
        """Execute sell order"""
        try:
            if limit_price:
                order = self.api.submit_order(
                    symbol=symbol, qty=qty, side='sell',
                    type='limit', time_in_force='ioc', limit_price=limit_price
                )
            else:
                order = self.api.submit_order(
                    symbol=symbol, qty=qty, side='sell',
                    type='market', time_in_force='ioc'
                )
            
            self.trades_today += 1
            logger.info(f"✅ SELL: {symbol} x{qty} | ID: {order.id}")
            return order
        except APIError as e:
            logger.error(f"❌ SELL FAILED ({symbol}): {e}")
            return None
    
    def close_position(self, symbol):
        """Close position"""
        try:
            self.api.close_position(symbol)
            logger.info(f"���� Position closed: {symbol}")
            return True
        except APIError as e:
            logger.error(f"Close error ({symbol}): {e}")
            return False

# ============================================================================
# AI PREDICTION ENGINE
# ============================================================================
class AIPredictor:
    """Advanced AI prediction engine"""
    
    @staticmethod
    def calculate_indicators(data):
        """Calculate technical indicators"""
        df = data.copy()
        
        # SMAs
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
        
        # ATR
        df['TR'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(abs(df['High'] - df['Close'].shift()),
                      abs(df['Low'] - df['Close'].shift()))
        )
        df['ATR'] = df['TR'].rolling(14).mean()
        
        # Volume
        df['Volume_SMA'] = df['Volume'].rolling(20).mean()
        df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
        
        return df.dropna()
    
    @staticmethod
    def predict(symbol, intraday_data, daily_data):
        """AI prediction engine - determines BUY/SELL/HOLD"""
        try:
            intraday = AIPredictor.calculate_indicators(intraday_data)
            daily = AIPredictor.calculate_indicators(daily_data)
            
            if len(intraday) < 2 or len(daily) < 2:
                return {'action': 'HOLD', 'confidence': 0, 'reasons': ['Insufficient data']}
            
            latest_intraday = intraday.iloc[-1]
            latest_daily = daily.iloc[-1]
            
            score = 0
            reasons = []
            
            # SMA signals
            if latest_daily['SMA_20'] > latest_daily['SMA_50']:
                score += 2
                reasons.append("SMA20 > SMA50 (Bullish)")
            else:
                score -= 2
                reasons.append("SMA20 < SMA50 (Bearish)")
            
            # Trend
            if latest_daily['SMA_50'] > latest_daily['SMA_200']:
                score += 1.5
                reasons.append("Uptrend confirmed")
            else:
                score -= 1.5
                reasons.append("Downtrend confirmed")
            
            # RSI
            rsi = latest_intraday['RSI']
            if rsi < 30:
                score += 2
                reasons.append("RSI Oversold (Buy signal)")
            elif rsi > 70:
                score -= 2
                reasons.append("RSI Overbought (Sell signal)")
            
            # MACD
            if latest_intraday['MACD'] > latest_intraday['MACD_Signal']:
                score += 1.5
                reasons.append("MACD Bullish")
            else:
                score -= 1.5
                reasons.append("MACD Bearish")
            
            # Bollinger Bands
            close = latest_intraday['Close']
            if close < latest_intraday['BB_Lower']:
                score += 1.5
                reasons.append("Below lower BB (Reversal)")
            elif close > latest_intraday['BB_Upper']:
                score -= 1.5
                reasons.append("Above upper BB (Reversal)")
            
            # Volume
            if latest_intraday['Volume_Ratio'] > 1.5:
                score += (1 if score > 0 else -1)
                reasons.append("High volume confirmation")
            
            # Volatility adjustment
            atr_pct = (latest_intraday['ATR'] / close) * 100
            if atr_pct > 2:
                score *= 0.8
                reasons.append("High volatility - reduced confidence")
            
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
                'reasons': reasons[:3],
                'rsi': round(rsi, 2)
            }
        
        except Exception as e:
            logger.error(f"Prediction error ({symbol}): {e}")
            return {'action': 'HOLD', 'confidence': 0, 'reasons': [str(e)]}

# ============================================================================
# QUANTUM FOX BOT
# ============================================================================
class QuantumFoxBot:
    """Autonomous AI Trading Bot"""
    
    def __init__(self, api_key, secret_key):
        self.client = TradingClient(api_key, secret_key)
        self.predictor = AIPredictor()
        self.selected_stocks = []
        self.daily_predictions = {}
        logger.info("🦊 Quantum Fox Bot Initialized")
    
    def select_top_stocks(self):
        """Select top 3 stocks for the day using AI"""
        logger.info("\n" + "="*60)
        logger.info("🌙 NIGHTLY ANALYSIS - Selecting Top 3 Stocks")
        logger.info("="*60)
        
        scores = {}
        
        for stock in TARGET_STOCKS:
            try:
                daily_data = yf.download(stock, period="6mo", interval="1d", progress=False)
                intraday_data = yf.download(stock, period="5d", interval="1h", progress=False)
                
                if daily_data.empty or intraday_data.empty:
                    continue
                
                prediction = self.predictor.predict(stock, intraday_data, daily_data)
                
                score = prediction['confidence']
                if prediction['action'] == 'BUY':
                    score *= 1.2
                elif prediction['action'] == 'SELL':
                    score *= 0.8
                
                scores[stock] = {'score': score, 'prediction': prediction}
                logger.info(f"  {stock}: {prediction['action']} | Conf: {prediction['confidence']}%")
            
            except Exception as e:
                logger.error(f"  {stock}: Error - {str(e)[:50]}")
                continue
        
        if not scores:
            logger.warning("No stocks analyzed")
            return []
        
        top_3 = sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True)[:TOP_N_STOCKS]
        self.selected_stocks = [s[0] for s in top_3]
        self.daily_predictions = {s[0]: s[1]['prediction'] for s in top_3}
        
        logger.info(f"\n✅ SELECTED: {self.selected_stocks}")
        for stock in self.selected_stocks:
            pred = self.daily_predictions[stock]
            logger.info(f"  {stock}: {pred['action']} | {pred['reasons'][0]}")
        
        logger.info("="*60 + "\n")
        return self.selected_stocks
    
    def execute_trading_cycle(self):
        """Execute trading cycle - buy low, sell high"""
        logger.info(f"\n{'='*60}")
        logger.info(f"🚀 TRADING CYCLE - {datetime.now().strftime('%H:%M:%S')}")
        logger.info(f"{'='*60}")
        
        if not self.selected_stocks:
            logger.warning("No stocks selected")
            return
        
        try:
            account = self.client.get_account()
            if not account:
                return
            
            portfolio_value = float(account.equity)
            position_value = portfolio_value * POSITION_SIZE
            
            logger.info(f"💰 Portfolio: ${portfolio_value:,.2f}")
            logger.info(f"📊 Position Size: ${position_value:,.2f}")
            logger.info(f"📈 Trades Today: {self.client.trades_today}/{MAX_DAILY_TRADES}")
            
            if self.client.trades_today >= MAX_DAILY_TRADES:
                logger.warning("❌ Daily limit reached!")
                return
            
            for stock in self.selected_stocks:
                if self.client.trades_today >= MAX_DAILY_TRADES:
                    break
                
                try:
                    intraday = yf.download(stock, period="1d", interval="1m", progress=False)
                    daily = yf.download(stock, period="6mo", interval="1d", progress=False)
                    
                    if intraday.empty or daily.empty:
                        continue
                    
                    prediction = self.predictor.predict(stock, intraday, daily)
                    current_price = intraday['Close'].iloc[-1]
                    
                    logger.info(f"\n📈 {stock} @ ${current_price:.2f}")
                    logger.info(f"  {prediction['action']} | Conf: {prediction['confidence']}%")
                    
                    positions = self.client.get_positions()
                    stock_pos = next((p for p in positions if p.symbol == stock), None)
                    
                    # BUY SIGNAL
                    if prediction['action'] == 'BUY' and prediction['confidence'] > 60:
                        qty = int(position_value / current_price)
                        if qty > 0:
                            limit_price = current_price * 0.9995
                            self.client.execute_buy(stock, qty, limit_price)
                    
                    # SELL SIGNAL
                    elif prediction['action'] == 'SELL' and stock_pos:
                        qty = int(float(stock_pos.qty))
                        entry_price = float(stock_pos.avg_entry_price)
                        
                        profit_target = entry_price * (1 + PROFIT_TARGET_PCT / 100)
                        stop_loss = entry_price * (1 - STOP_LOSS_PCT / 100)
                        
                        if current_price >= profit_target:
                            logger.info(f"  💰 Profit target! Selling at ${current_price:.2f}")
                            self.client.execute_sell(stock, qty, current_price * 1.0005)
                        elif current_price <= stop_loss:
                            logger.warning(f"  🛑 Stop loss! Selling at ${current_price:.2f}")
                            self.client.execute_sell(stock, qty)
                        elif prediction['confidence'] > 70:
                            self.client.execute_sell(stock, qty, current_price * 1.0005)
                
                except Exception as e:
                    logger.error(f"Error trading {stock}: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Cycle error: {e}")
        
        logger.info(f"{'='*60}\n")
    
    def scheduled_nightly_analysis(self):
        """Nightly analysis at 9:00 PM ET"""
        self.select_top_stocks()
    
    def scheduled_intraday_trading(self):
        """Intraday trading every 15 min (market hours)"""
        now = datetime.now()
        hour = now.hour
        minute = now.minute
        
        # Market hours: 9:30 AM - 4:00 PM ET
        if 9 <= hour < 16 and (hour != 9 or minute >= 30):
            self.execute_trading_cycle()
    
    def start(self):
        """Start the bot"""
        logger.info("\n" + "="*60)
        logger.info("🦊 QUANTUM FOX - AUTONOMOUS TRADING BOT")
        logger.info("="*60)
        logger.info(f"✅ Status: LIVE TRADING")
        logger.info(f"📊 Top Stocks: {TOP_N_STOCKS}")
        logger.info(f"📈 Max Trades/Day: {MAX_DAILY_TRADES}")
        logger.info(f"💰 Position Size: {POSITION_SIZE*100}%")
        logger.info(f"🎯 Profit Target: {PROFIT_TARGET_PCT}%")
        logger.info(f"🛑 Stop Loss: {STOP_LOSS_PCT}%")
        logger.info("="*60)
        logger.info("📅 Schedule:")
        logger.info("  - Nightly Analysis: 21:00 ET")
        logger.info("  - Intraday Trading: Every 15 min (9:30 AM - 4:00 PM ET)")
        logger.info("="*60 + "\n")
        
        # Setup scheduler
        schedule.every().day.at("21:00").do(self.scheduled_nightly_analysis)
        schedule.every(15).minutes.do(self.scheduled_intraday_trading)
        
        logger.info("✅ Scheduler started\n")
        
        # Run forever
        while True:
            schedule.run_pending()
            time.sleep(60)

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    try:
        bot = QuantumFoxBot(ALPACA_API_KEY, ALPACA_SECRET_KEY)
        bot.start()
    except KeyboardInterrupt:
        logger.info("\n🛑 Bot stopped")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yfinance as yf
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import logging
import numpy as np

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# FASTAPI APP CONFIGURATION
# ============================================================================
app = FastAPI(
    title="Quantum Fox API",
    description="AI-Powered Trading API with real-time market analysis",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# MODELS
# ============================================================================
class TradeRequest(BaseModel):
    symbol: str
    action: str  # "buy" or "sell"
    quantity: int
    order_type: str = "market"  # "market" or "limit"
    limit_price: float = None
    stop_loss_pct: float = 0
    take_profit_pct: float = 0

class StockDataRequest(BaseModel):
    symbol: str
    period: str = "1mo"
    interval: str = "1d"

class PredictionResponse(BaseModel):
    symbol: str
    action: str
    confidence: float
    signals: dict

class TradeResponse(BaseModel):
    status: str
    order_id: str = None
    message: str

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_technical_indicators(hist):
    """Calculate SMA, RSI, MACD"""
    indicators = {}
    
    try:
        # SMA
        hist['SMA20'] = hist['Close'].rolling(20).mean()
        hist['SMA50'] = hist['Close'].rolling(50).mean()
        
        last = hist.dropna().iloc[-1]
        if last['SMA20'] > last['SMA50']:
            indicators['sma_signal'] = 'BUY'
        elif last['SMA20'] < last['SMA50']:
            indicators['sma_signal'] = 'SELL'
        else:
            indicators['sma_signal'] = 'HOLD'
        
        # RSI
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        last_rsi = rsi.iloc[-1]
        
        indicators['rsi'] = round(last_rsi, 2)
        if last_rsi > 70:
            indicators['rsi_signal'] = 'OVERBOUGHT'
        elif last_rsi < 30:
            indicators['rsi_signal'] = 'OVERSOLD'
        else:
            indicators['rsi_signal'] = 'NEUTRAL'
        
        # MACD
        exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
        exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=9, adjust=False).mean()
        
        last_macd = macd.iloc[-1]
        last_signal = signal_line.iloc[-1]
        
        indicators['macd'] = round(last_macd, 4)
        if last_macd > last_signal:
            indicators['macd_signal'] = 'BULLISH'
        else:
            indicators['macd_signal'] = 'BEARISH'
        
    except Exception as e:
        logger.error(f"Technical indicator calculation error: {e}")
        indicators = {
            'sma_signal': 'HOLD',
            'rsi': 0,
            'rsi_signal': 'N/A',
            'macd': 0,
            'macd_signal': 'N/A'
        }
    
    return indicators

def get_alpaca_api():
    """Initialize Alpaca API client"""
    try:
        alpaca_key = os.getenv("ALPACA_API_KEY")
        alpaca_secret = os.getenv("ALPACA_SECRET_KEY")
        alpaca_env = os.getenv("ALPACA_ENV", "paper").lower()
        
        if not alpaca_key or not alpaca_secret:
            raise ValueError("Alpaca API credentials not found in environment variables")
        
        endpoint = "https://paper-api.alpaca.markets" if alpaca_env == "paper" else "https://api.alpaca.markets"
        api = tradeapi.REST(alpaca_key, alpaca_secret, base_url=endpoint, api_version='v2')
        return api
    except Exception as e:
        logger.error(f"Alpaca API initialization error: {e}")
        return None

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - API status"""
    return {
        "status": "✅ Online",
        "name": "Quantum Fox Trading API",
        "version": "1.0.0",
        "endpoints": {
            "stock": "/stock/{symbol}",
            "predict": "/predict/{symbol}",
            "trade": "/trade",
            "account": "/account",
            "positions": "/positions"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ============================================================================
# STOCK DATA ENDPOINTS
# ============================================================================

@app.get("/stock/{symbol}")
async def get_stock(symbol: str, period: str = "1d"):
    """
    Fetch current stock price and basic data
    
    Args:
        symbol: Stock ticker (e.g., AAPL)
        period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y)
    
    Returns:
        Stock price, high, low, volume, change
    """
    try:
        symbol = symbol.upper().strip()
        
        stock = yf.Ticker(symbol)
        data = stock.history(period=period)
        
        if data.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        latest = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else latest
        
        price_change = latest['Close'] - prev['Close']
        price_change_pct = (price_change / prev['Close'] * 100) if prev['Close'] != 0 else 0
        
        return {
            "symbol": symbol,
            "price": round(latest['Close'], 2),
            "high": round(latest['High'], 2),
            "low": round(latest['Low'], 2),
            "volume": int(latest['Volume']),
            "change": round(price_change, 2),
            "change_percent": round(price_change_pct, 2),
            "timestamp": latest.name.isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stock fetch error for {symbol}: {e}")
        raise HTTPException(status_code=400, detail=f"Error fetching stock data: {str(e)}")

@app.get("/stock/{symbol}/history")
async def get_stock_history(symbol: str, period: str = "1mo", interval: str = "1d"):
    """
    Fetch historical stock data
    
    Args:
        symbol: Stock ticker
        period: Lookback period (1d, 5d, 1mo, 3mo, 6mo, 1y)
        interval: Candle interval (1m, 5m, 15m, 1h, 1d)
    
    Returns:
        OHLCV data
    """
    try:
        symbol = symbol.upper().strip()
        
        data = yf.download(symbol, period=period, interval=interval, progress=False)
        
        if data.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        # Convert to JSON-serializable format
        records = []
        for date, row in data.iterrows():
            records.append({
                "date": date.isoformat(),
                "open": round(row['Open'], 2),
                "high": round(row['High'], 2),
                "low": round(row['Low'], 2),
                "close": round(row['Close'], 2),
                "volume": int(row['Volume'])
            })
        
        return {
            "symbol": symbol,
            "period": period,
            "interval": interval,
            "data": records
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Stock history error for {symbol}: {e}")
        raise HTTPException(status_code=400, detail=f"Error fetching history: {str(e)}")

# ============================================================================
# PREDICTION & ANALYSIS ENDPOINTS
# ============================================================================

@app.get("/predict/{symbol}")
async def predict_trade(symbol: str):
    """
    AI trade signal prediction based on technical indicators
    
    Args:
        symbol: Stock ticker
    
    Returns:
        Predicted action (BUY/SELL/HOLD) with confidence level
    """
    try:
        symbol = symbol.upper().strip()
        
        # Fetch 3-month data for indicators
        hist = yf.download(symbol, period="3mo", interval="1d", progress=False)
        
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        # Calculate indicators
        indicators = calculate_technical_indicators(hist)
        
        # Weighted voting system
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        # SMA signal
        sma_signal = indicators.get('sma_signal', 'HOLD')
        votes[sma_signal] += 2
        
        # RSI signal
        rsi_signal = indicators.get('rsi_signal', 'NEUTRAL')
        if rsi_signal == 'OVERSOLD':
            votes['BUY'] += 1
        elif rsi_signal == 'OVERBOUGHT':
            votes['SELL'] += 1
        else:
            votes['HOLD'] += 1
        
        # MACD signal
        macd_signal = indicators.get('macd_signal', 'NEUTRAL')
        if macd_signal == 'BULLISH':
            votes['BUY'] += 1
        else:
            votes['SELL'] += 1
        
        # Determine action
        action = max(votes, key=votes.get)
        confidence = (votes[action] / sum(votes.values())) * 100
        
        return {
            "symbol": symbol,
            "action": action,
            "confidence": round(confidence, 2),
            "signals": indicators,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prediction error for {symbol}: {e}")
        raise HTTPException(status_code=400, detail=f"Error generating prediction: {str(e)}")

# ============================================================================
# TRADING ENDPOINTS
# ============================================================================

@app.post("/trade")
async def execute_trade(trade: TradeRequest):
    """
    Execute a trade order via Alpaca
    
    Args:
        symbol: Stock ticker
        action: BUY or SELL
        quantity: Number of shares
        order_type: market or limit
        limit_price: Price for limit orders
        stop_loss_pct: Stop loss percentage
        take_profit_pct: Take profit percentage
    
    Returns:
        Order confirmation
    """
    try:
        # Validate input
        if trade.action.lower() not in ["buy", "sell"]:
            raise HTTPException(status_code=400, detail="Action must be 'buy' or 'sell'")
        
        if trade.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be positive")
        
        if trade.order_type.lower() not in ["market", "limit"]:
            raise HTTPException(status_code=400, detail="Order type must be 'market' or 'limit'")
        
        if trade.order_type.lower() == "limit" and trade.limit_price is None:
            raise HTTPException(status_code=400, detail="Limit price required for limit orders")
        
        # Get API client
        api = get_alpaca_api()
        if api is None:
            raise HTTPException(status_code=503, detail="Broker connection unavailable")
        
        # Place main order
        order_data = {
            "symbol": trade.symbol.upper().strip(),
            "qty": trade.quantity,
            "side": trade.action.lower(),
            "type": trade.order_type.lower(),
            "time_in_force": "gtc"
        }
        
        if trade.order_type.lower() == "limit":
            order_data["limit_price"] = trade.limit_price
        
        order = api.submit_order(**order_data)
        
        logger.info(f"Order placed: {order.id} - {trade.symbol} {trade.action} {trade.quantity}")
        
        return {
            "status": "executed",
            "order_id": order.id,
            "symbol": trade.symbol.upper(),
            "action": trade.action.lower(),
            "quantity": trade.quantity,
            "order_type": trade.order_type,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade execution error: {e}")
        raise HTTPException(status_code=400, detail=f"Trade failed: {str(e)}")

# ============================================================================
# ACCOUNT ENDPOINTS
# ============================================================================

@app.get("/account")
async def get_account():
    """Get account information"""
    try:
        api = get_alpaca_api()
        if api is None:
            raise HTTPException(status_code=503, detail="Broker connection unavailable")
        
        account = api.get_account()
        
        return {
            "status": account.status,
            "equity": round(float(account.equity), 2),
            "cash": round(float(account.cash), 2),
            "buying_power": round(float(account.buying_power), 2),
            "portfolio_value": round(float(account.portfolio_value), 2),
            "account_type": account.account_type,
            "multiplier": account.multiplier,
            "daytrading_buying_power": round(float(account.daytrading_buying_power), 2)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account fetch error: {e}")
        raise HTTPException(status_code=400, detail=f"Error fetching account: {str(e)}")

@app.get("/positions")
async def get_positions():
    """Get open positions"""
    try:
        api = get_alpaca_api()
        if api is None:
            raise HTTPException(status_code=503, detail="Broker connection unavailable")
        
        positions = api.list_positions()
        
        pos_list = []
        for pos in positions:
            pos_list.append({
                "symbol": pos.symbol,
                "quantity": int(float(pos.qty)),
                "entry_price": round(float(pos.avg_entry_price), 2),
                "current_price": round(float(pos.current_price), 2),
                "market_value": round(float(pos.market_value), 2),
                "unrealized_pl": round(float(pos.unrealized_pl), 2),
                "unrealized_plpc": round(float(pos.unrealized_plpc) * 100, 2)
            })
        
        return {
            "positions": pos_list,
            "total_positions": len(pos_list),
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Positions fetch error: {e}")
        raise HTTPException(status_code=400, detail=f"Error fetching positions: {str(e)}")

@app.post("/close-position/{symbol}")
async def close_position(symbol: str):
    """Close an open position"""
    try:
        api = get_alpaca_api()
        if api is None:
            raise HTTPException(status_code=503, detail="Broker connection unavailable")
        
        api.close_position(symbol.upper().strip())
        
        logger.info(f"Position closed: {symbol}")
        
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "message": f"Position {symbol} closed successfully"
        }
    
    except Exception as e:
        logger.error(f"Close position error: {e}")
        raise HTTPException(status_code=400, detail=f"Error closing position: {str(e)}")

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "error": True,
        "status_code": exc.status_code,
        "detail": exc.detail,
        "timestamp": datetime.now().isoformat()
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": True,
        "status_code": 500,
        "detail": "Internal server error",
        "timestamp": datetime.now().isoformat()
    }

# ============================================================================
# STARTUP/SHUTDOWN EVENTS
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("🦊 Quantum Fox API Starting...")
    logger.info("✅ FastAPI server initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    logger.info("🦊 Quantum Fox API Shutting Down...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

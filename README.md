# Quantum Fox 🦊 — AI-Powered Live Trading Dashboard

> **Real-time market analysis | Smart order execution | Maximum profit potential**

## ⚠️ DISCLAIMER - LIVE TRADING

This application executes **REAL trades with actual money** via Alpaca. Use responsibly and at your own risk.

- 🔴 **NOT a simulation** — All trades are executed on live accounts
- 💰 **Real capital at risk** — Only use funds you can afford to lose
- 📊 **No guarantees** — Past performance does not guarantee future results
- 🛑 **Always use stop losses** — Risk management is critical

---

## 🚀 Features

✅ **Real-time Market Analysis**
- Live candlestick charts with volume
- Technical indicators (SMA, RSI, MACD)
- AI-powered trade signals

✅ **Smart Order Execution**
- Market & limit orders
- Automatic stop loss & take profit
- Risk management tools

✅ **Portfolio Management**
- Open positions tracking
- Real-time P&L monitoring
- Close positions instantly

✅ **Performance Dashboard**
- Account equity & buying power
- Trade history
- Account status overview

---

## 📋 Prerequisites

- **Python 3.9+**
- **Alpaca Trading Account** (Live or Paper for testing)
- **API Keys** from Alpaca (https://alpaca.markets)

---

## 🔧 Installation

### 1. Clone the repository
```bash
git clone https://github.com/chrisyep90-debug/quantum-fox.git
cd quantum-fox
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API credentials
```bash
# Copy example to .env file
cp .env.example .env

# Edit .env with your Alpaca API keys
# ALPACA_API_KEY=your_key_here
# ALPACA_SECRET_KEY=your_secret_here
# ALPACA_ENV=live
```

---

## ▶️ Running the Application

### Option 1: Frontend Only (Streamlit)
```bash
streamlit run app.py
```
Visit `http://localhost:8501`

### Option 2: Backend + Frontend (Full Stack)

**Terminal 1 - Start Backend API:**
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
API available at: `http://localhost:8000`
API docs at: `http://localhost:8000/docs`

**Terminal 2 - Start Frontend:**
```bash
streamlit run app.py
```
Frontend available at: `http://localhost:8501`

---

## 📚 API Endpoints

### Market Data
- `GET /stock/{symbol}` - Get current stock price
- `GET /stock/{symbol}/history` - Get historical data

### Analysis
- `GET /predict/{symbol}` - Get AI trade signal

### Trading
- `POST /trade` - Execute trade order
- `POST /close-position/{symbol}` - Close position

### Account
- `GET /account` - Get account info
- `GET /positions` - List open positions

Full API documentation: `http://localhost:8000/docs`

---

## 🎯 Dashboard Features

### 📊 Market Analysis Tab
- Search any stock symbol
- View interactive candlestick charts
- Technical indicator analysis (SMA, RSI, MACD)
- AI trading signals

### 🚀 Place Order Tab
- Market & limit order execution
- Risk management (stop loss, take profit)
- Order preview before execution
- Real-time position updates

### 📈 Positions Tab
- View all open positions
- Profit/loss tracking
- Close positions instantly
- Market value updates

### 📊 Performance Tab
- Account equity & cash
- Buying power display
- Trade history
- Account status details

---

## 🔐 Security

- **Never commit `.env` file** — Use `.env.example` as template
- **API keys stored locally** — Only in `.env` file
- **Environment variables** — Loaded from `.env` at runtime
- **Live trading** — Requires valid Alpaca credentials

---

## ⚡ Quick Start Example

1. **Start the app:**
   ```bash
   streamlit run app.py
   ```

2. **Enter Alpaca API credentials in sidebar**

3. **Select a stock** (e.g., AAPL)

4. **View technical analysis** & AI signals

5. **Place a trade** with risk management

6. **Monitor positions** in real-time

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Streamlit, Plotly |
| **Backend** | FastAPI, Uvicorn |
| **Data** | yfinance, Pandas, NumPy |
| **Trading** | Alpaca Trade API |
| **Config** | python-dotenv |

---

## 📊 Trading Signals

### SMA Crossover (Simple Moving Average)
- **BUY** when SMA20 > SMA50
- **SELL** when SMA20 < SMA50
- **Weight:** 2x

### RSI (Relative Strength Index)
- **OVERSOLD** (RSI < 30) → Potential BUY
- **OVERBOUGHT** (RSI > 70) → Potential SELL
- **NEUTRAL** (30-70) → HOLD
- **Weight:** 1x

### MACD (Moving Average Convergence Divergence)
- **BULLISH** when MACD > Signal Line → BUY
- **BEARISH** when MACD < Signal Line → SELL
- **Weight:** 1x

**Final Action:** Weighted voting system determines BUY/SELL/HOLD

---

## 💡 Best Practices

✅ **DO:**
- Always use stop losses
- Start with small positions
- Test with paper trading first (if using paper account)
- Monitor positions actively
- Keep API keys secure
- Review daily P&L

❌ **DON'T:**
- Trade with money you need
- Ignore risk management
- Leave positions unmonitored
- Share API credentials
- Trade based on emotions
- Over-leverage positions

---

## 🐛 Troubleshooting

### Connection Error: "Alpaca connection failed"
- Check API key validity
- Verify environment variables in `.env`
- Ensure internet connectivity
- Check Alpaca account status

### No Data Available
- Verify stock symbol (e.g., AAPL, not APPLE)
- Check market hours (9:30 AM - 4:00 PM EST weekdays)
- Ensure stock is actively trading

### Order Failed
- Insufficient buying power
- Market/exchange closed
- Invalid order parameters
- Symbol not tradable

---

## 📞 Support

- **Alpaca Docs:** https://alpaca.markets/docs
- **Streamlit Docs:** https://docs.streamlit.io
- **FastAPI Docs:** https://fastapi.tiangolo.com

---

## 📄 License

This project is provided as-is for educational purposes. Trading involves risk.

---

## ⚠️ Final Warning

**THIS IS A LIVE TRADING APPLICATION. ALL TRADES ARE EXECUTED WITH REAL MONEY.**

- You are responsible for all trading decisions
- Past performance does not guarantee future results
- Always use proper risk management
- Never trade with capital you cannot afford to lose
- Start small and increase position size gradually

---

**Happy Trading! 🦊📈💰**

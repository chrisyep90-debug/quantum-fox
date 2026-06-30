import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import alpaca_trade_api as tradeapi
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# ============================================================================
# PAGE CONFIG & THEME
# ============================================================================
st.set_page_config(
    page_title="Quantum Fox 🦊 Live Trading",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Quantum Fox — AI-Powered Live Trading Dashboard"
    }
)

# Custom CSS for bright, professional theme
st.markdown("""
<style>
    :root {
        --primary-color: #00D084;
        --background-color: #0F1419;
        --surface-color: #1A1F2E;
        --text-color: #FFFFFF;
    }
    
    .main {
        background-color: #0F1419;
        color: #FFFFFF;
    }
    
    .stMetric {
        background-color: #1A1F2E;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #00D084;
    }
    
    .profit {
        color: #00D084;
        font-weight: bold;
    }
    
    .loss {
        color: #FF4757;
        font-weight: bold;
    }
    
    .neutral {
        color: #FFB800;
        font-weight: bold;
    }
    
    h1, h2, h3 {
        color: #00D084;
    }
    
    .header-banner {
        background: linear-gradient(135deg, #00D084 0%, #00A86B 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE & CACHING
# ============================================================================
if 'connected' not in st.session_state:
    st.session_state.connected = False
if 'api' not in st.session_state:
    st.session_state.api = None
if 'trades_history' not in st.session_state:
    st.session_state.trades_history = []

@st.cache_data(ttl=60)
def fetch_stock_data(symbol, period, interval):
    """Cached stock data fetching for performance"""
    try:
        data = yf.download(symbol, period=period, interval=interval, progress=False)
        return data
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

@st.cache_data(ttl=300)
def fetch_ticker_info(symbol):
    """Cached ticker information"""
    try:
        ticker = yf.Ticker(symbol)
        return ticker.info
    except Exception as e:
        return None

# ============================================================================
# HEADER
# ============================================================================
st.markdown("""
<div class="header-banner">
    <h1>🦊 Quantum Fox — AI Trading Dashboard</h1>
    <p>Real-time market analysis | Smart order execution | Maximum profit potential</p>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR: BROKER CONFIGURATION
# ============================================================================
with st.sidebar:
    st.header("⚙️ Broker Configuration")
    
    # API Key Input
    st.subheader("Alpaca API Settings")
    use_env_keys = st.checkbox("Load keys from .env file", value=True)
    
    if use_env_keys:
        alpaca_key = os.getenv("ALPACA_API_KEY", "")
        alpaca_secret = os.getenv("ALPACA_SECRET_KEY", "")
        alpaca_env = os.getenv("ALPACA_ENV", "paper").lower()
    else:
        alpaca_key = st.text_input("API Key", type="password", value="")
        alpaca_secret = st.text_input("Secret Key", type="password", value="")
        alpaca_env = st.selectbox("Environment", ["paper", "live"], index=0)
    
    # Environment selection
    st.divider()
    st.subheader("Trading Mode")
    if alpaca_env == "paper":
        st.success("📄 PAPER MODE — Safe for testing")
    else:
        st.error("🔴 LIVE MODE — REAL MONEY AT RISK")
    
    trading_mode = st.radio("Select Mode", ["Paper", "Live"], index=0)
    alpaca_env = "paper" if trading_mode == "Paper" else "live"
    
    # Connection status
    st.divider()
    st.subheader("Connection Status")
    
    api = None
    account_info = None
    
    if alpaca_key and alpaca_secret:
        endpoint = "https://paper-api.alpaca.markets" if alpaca_env == "paper" else "https://api.alpaca.markets"
        
        try:
            api = tradeapi.REST(alpaca_key, alpaca_secret, base_url=endpoint, api_version='v2')
            account_info = api.get_account()
            st.session_state.api = api
            st.session_state.connected = True
            
            # Display connection info
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Status", "✅ Connected", border=True)
            with col2:
                st.metric("Mode", "PAPER" if alpaca_env == "paper" else "LIVE", border=True)
            
            # Account Summary
            st.subheader("Account Summary")
            equity = float(account_info.equity)
            cash = float(account_info.cash)
            buying_power = float(account_info.buying_power)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Equity", f"${equity:,.2f}")
            with col2:
                st.metric("Cash", f"${cash:,.2f}")
            with col3:
                st.metric("Buying Power", f"${buying_power:,.2f}")
            
        except Exception as e:
            st.error(f"❌ Connection Failed: {str(e)[:100]}")
            st.session_state.connected = False
            st.session_state.api = None
    else:
        st.warning("⚠️ Enter API credentials to connect")
        st.session_state.connected = False
        st.session_state.api = None
    
    # Risk warnings
    st.divider()
    st.warning("""
    ⚠️ **TRADING DISCLAIMER**
    - Use PAPER mode first
    - Live trading risks real money
    - Past performance ≠ Future results
    - Always use stop losses
    - Trade responsibly
    """)

# ============================================================================
# MAIN DASHBOARD
# ============================================================================

# Tab layout for organization
tab1, tab2, tab3, tab4 = st.tabs(["📊 Market Analysis", "🚀 Place Order", "📈 Positions", "📊 Performance"])

# ============================================================================
# TAB 1: MARKET ANALYSIS
# ============================================================================
with tab1:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        symbol = st.text_input("Stock Symbol", value="AAPL", help="Enter stock ticker (e.g., AAPL, GOOGL, TSLA)").upper().strip()
    
    with col2:
        period = st.selectbox("Period", ['1d', '5d', '1mo', '3mo', '6mo', '1y'], index=1, help="Data lookback period")
    
    with col3:
        interval = st.selectbox("Interval", ['1m', '5m', '15m', '1h', '1d'], index=3, help="Candlestick interval")
    
    if symbol:
        try:
            # Fetch data
            with st.spinner(f"Loading {symbol} data..."):
                data = fetch_stock_data(symbol, period, interval)
            
            if data is not None and not data.empty:
                # Display current price
                latest_price = data['Close'].iloc[-1]
                prev_price = data['Close'].iloc[-2] if len(data) > 1 else latest_price
                price_change = latest_price - prev_price
                price_change_pct = (price_change / prev_price * 100) if prev_price != 0 else 0
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        f"Current Price",
                        f"${latest_price:.2f}",
                        delta=f"{price_change_pct:+.2f}%",
                        delta_color="off" if price_change_pct == 0 else "normal"
                    )
                
                with col2:
                    st.metric("High (24h)", f"${data['High'].iloc[-1]:.2f}")
                
                with col3:
                    st.metric("Low (24h)", f"${data['Low'].iloc[-1]:.2f}")
                
                with col4:
                    volume = data['Volume'].iloc[-1]
                    st.metric("Volume", f"{volume:,.0f}" if volume > 0 else "N/A")
                
                # Candlestick Chart
                st.subheader(f"{symbol} Price Chart")
                
                # Create candlestick chart with volume
                fig = make_subplots(
                    rows=2, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.1,
                    row_heights=[0.7, 0.3]
                )
                
                fig.add_trace(
                    go.Candlestick(
                        x=data.index,
                        open=data['Open'],
                        high=data['High'],
                        low=data['Low'],
                        close=data['Close'],
                        name="Price",
                        increasing_line_color='#00D084',
                        decreasing_line_color='#FF4757'
                    ),
                    row=1, col=1
                )
                
                # Add volume bars
                colors = ['#00D084' if close >= open_ else '#FF4757' 
                         for close, open_ in zip(data['Close'], data['Open'])]
                
                fig.add_trace(
                    go.Bar(
                        x=data.index,
                        y=data['Volume'],
                        name="Volume",
                        marker_color=colors,
                        showlegend=False
                    ),
                    row=2, col=1
                )
                
                fig.update_layout(
                    height=600,
                    title=f"{symbol} — {period} Chart",
                    yaxis_title="Price (USD)",
                    yaxis2_title="Volume",
                    xaxis_rangeslider_visible=False,
                    template="plotly_dark",
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Technical Indicators
                st.subheader("📊 Technical Indicators")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.subheader("SMA Crossover Signal")
                    try:
                        hist = yf.download(symbol, period='2mo', interval='1d', progress=False)
                        hist['SMA20'] = hist['Close'].rolling(20).mean()
                        hist['SMA50'] = hist['Close'].rolling(50).mean()
                        
                        last = hist.dropna().iloc[-1]
                        signal = 'HOLD'
                        signal_color = 'neutral'
                        
                        if last['SMA20'] > last['SMA50']:
                            signal = '🟢 BUY'
                            signal_color = 'profit'
                        elif last['SMA20'] < last['SMA50']:
                            signal = '🔴 SELL'
                            signal_color = 'loss'
                        
                        st.markdown(f"<h3 class='{signal_color}'>{signal}</h3>", unsafe_allow_html=True)
                        st.caption(f"SMA20: ${last['SMA20']:.2f} | SMA50: ${last['SMA50']:.2f}")
                    except Exception as e:
                        st.info("Not enough data for SMA signal.")
                
                with col2:
                    st.subheader("RSI (14)")
                    try:
                        delta = hist['Close'].diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi = 100 - (100 / (1 + rs))
                        
                        last_rsi = rsi.iloc[-1]
                        
                        if last_rsi > 70:
                            rsi_signal = "🔴 OVERBOUGHT"
                            rsi_color = "loss"
                        elif last_rsi < 30:
                            rsi_signal = "🟢 OVERSOLD"
                            rsi_color = "profit"
                        else:
                            rsi_signal = "🟡 NEUTRAL"
                            rsi_color = "neutral"
                        
                        st.markdown(f"<h3 class='{rsi_color}'>{last_rsi:.1f}</h3>", unsafe_allow_html=True)
                        st.caption(rsi_signal)
                    except Exception as e:
                        st.info("RSI calculation failed.")
                
                with col3:
                    st.subheader("MACD Signal")
                    try:
                        exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
                        exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
                        macd = exp1 - exp2
                        signal_line = macd.ewm(span=9, adjust=False).mean()
                        
                        last_macd = macd.iloc[-1]
                        last_signal = signal_line.iloc[-1]
                        
                        if last_macd > last_signal:
                            macd_signal = "🟢 BULLISH"
                            macd_color = "profit"
                        else:
                            macd_signal = "🔴 BEARISH"
                            macd_color = "loss"
                        
                        st.markdown(f"<h3 class='{macd_color}'>{macd_signal}</h3>", unsafe_allow_html=True)
                        st.caption(f"MACD: {last_macd:.4f} | Signal: {last_signal:.4f}")
                    except Exception as e:
                        st.info("MACD calculation failed.")
            else:
                st.error(f"No data available for {symbol}")
        
        except Exception as e:
            st.error(f"Error loading chart: {e}")

# ============================================================================
# TAB 2: PLACE ORDER
# ============================================================================
with tab2:
    if not st.session_state.connected:
        st.error("❌ Please connect to Alpaca in the sidebar first")
    else:
        st.subheader("🚀 Execute Trade")
        
        col1, col2 = st.columns(2)
        
        with col1:
            order_symbol = st.text_input("Symbol", value=symbol, help="Stock ticker").upper().strip()
            order_quantity = st.number_input("Quantity (shares)", min_value=1, value=1, step=1)
            order_side = st.selectbox("Action", ["BUY", "SELL"], index=0)
        
        with col2:
            order_type = st.selectbox("Order Type", ["Market", "Limit"], index=0)
            
            if order_type == "Limit":
                limit_price = st.number_input("Limit Price", min_value=0.01, value=100.00, step=0.01)
            else:
                limit_price = None
            
            time_in_force = st.selectbox("Time in Force", ["Day", "GTC"], index=0)
        
        # Risk Management
        st.subheader("📍 Risk Management")
        col1, col2 = st.columns(2)
        
        with col1:
            use_stop_loss = st.checkbox("Set Stop Loss", value=True)
            if use_stop_loss:
                stop_loss_pct = st.slider("Stop Loss %", min_value=0.1, max_value=10.0, value=2.0, step=0.1)
            else:
                stop_loss_pct = 0
        
        with col2:
            use_take_profit = st.checkbox("Set Take Profit", value=True)
            if use_take_profit:
                take_profit_pct = st.slider("Take Profit %", min_value=0.1, max_value=20.0, value=5.0, step=0.1)
            else:
                take_profit_pct = 0
        
        # Order preview
        st.subheader("Order Preview")
        if order_symbol:
            try:
                current_price = yf.Ticker(order_symbol).info.get('currentPrice', 0)
                if current_price == 0:
                    data = yf.download(order_symbol, period='1d', progress=False)
                    current_price = data['Close'].iloc[-1] if not data.empty else 0
                
                if current_price > 0:
                    order_value = order_quantity * current_price
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Order Value", f"${order_value:,.2f}")
                    with col2:
                        if use_stop_loss:
                            sl_price = current_price * (1 - stop_loss_pct/100) if order_side == "BUY" else current_price * (1 + stop_loss_pct/100)
                            st.metric("Stop Loss", f"${sl_price:.2f}")
                    with col3:
                        if use_take_profit:
                            tp_price = current_price * (1 + take_profit_pct/100) if order_side == "BUY" else current_price * (1 - take_profit_pct/100)
                            st.metric("Take Profit", f"${tp_price:.2f}")
            except Exception as e:
                st.warning(f"Could not fetch price: {e}")
        
        # Place Order Button
        st.divider()
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🚀 PLACE ORDER", use_container_width=True):
                if not order_symbol:
                    st.error("Enter a symbol")
                elif st.session_state.api is None:
                    st.error("API connection lost")
                else:
                    try:
                        tif = "day" if time_in_force == "Day" else "gtc"
                        order_data = {
                            "symbol": order_symbol,
                            "qty": order_quantity,
                            "side": order_side.lower(),
                            "type": order_type.lower(),
                            "time_in_force": tif
                        }
                        
                        if order_type == "Limit" and limit_price:
                            order_data["limit_price"] = limit_price
                        
                        order = st.session_state.api.submit_order(**order_data)
                        
                        st.success(f"✅ Order Placed! ID: {order.id}")
                        st.balloons()
                        
                        # Store in history
                        st.session_state.trades_history.append({
                            "timestamp": datetime.now(),
                            "symbol": order_symbol,
                            "side": order_side,
                            "quantity": order_quantity,
                            "status": order.status,
                            "order_id": order.id
                        })
                        
                        time.sleep(2)
                        st.rerun()
                    
                    except Exception as e:
                        st.error(f"❌ Order Failed: {str(e)}")
        
        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                st.info("Order placement cancelled")

# ============================================================================
# TAB 3: POSITIONS
# ============================================================================
with tab3:
    if not st.session_state.connected:
        st.error("❌ Connect to Alpaca to view positions")
    else:
        st.subheader("📈 Open Positions")
        
        try:
            positions = st.session_state.api.list_positions()
            
            if positions:
                pos_data = []
                total_profit_loss = 0
                
                for pos in positions:
                    profit_loss = float(pos.unrealized_pl)
                    profit_loss_pct = float(pos.unrealized_plpc) * 100
                    total_profit_loss += profit_loss
                    
                    pos_data.append({
                        "Symbol": pos.symbol,
                        "Qty": int(float(pos.qty)),
                        "Entry Price": f"${float(pos.avg_entry_price):.2f}",
                        "Current Price": f"${float(pos.current_price):.2f}",
                        "Market Value": f"${float(pos.market_value):,.2f}",
                        "P&L": f"${profit_loss:,.2f}",
                        "P&L %": f"{profit_loss_pct:+.2f}%"
                    })
                
                # Display positions table
                df_positions = pd.DataFrame(pos_data)
                st.dataframe(df_positions, use_container_width=True, hide_index=True)
                
                # Total P&L
                st.divider()
                col1, col2 = st.columns(2)
                with col1:
                    if total_profit_loss >= 0:
                        st.metric("Total Unrealized P&L", f"${total_profit_loss:,.2f}", 
                                delta=None, delta_color="off")
                    else:
                        st.metric("Total Unrealized P&L", f"${total_profit_loss:,.2f}", 
                                delta=None, delta_color="off")
                
                # Close position option
                st.subheader("Close Position")
                close_symbol = st.selectbox("Select Position to Close", [p.symbol for p in positions])
                
                if st.button("🔒 Close Position"):
                    try:
                        st.session_state.api.close_position(close_symbol)
                        st.success(f"✅ Position {close_symbol} closed!")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error closing position: {e}")
            
            else:
                st.info("📭 No open positions")
        
        except Exception as e:
            st.error(f"Error fetching positions: {e}")

# ============================================================================
# TAB 4: PERFORMANCE
# ============================================================================
with tab4:
    st.subheader("📊 Trading Performance")
    
    if not st.session_state.connected:
        st.error("❌ Connect to Alpaca to view performance")
    else:
        try:
            account = st.session_state.api.get_account()
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Equity", f"${float(account.equity):,.2f}")
            
            with col2:
                st.metric("Total Cash", f"${float(account.cash):,.2f}")
            
            with col3:
                buying_power = float(account.buying_power)
                st.metric("Buying Power", f"${buying_power:,.2f}")
            
            with col4:
                portfolio_value = float(account.portfolio_value)
                st.metric("Portfolio Value", f"${portfolio_value:,.2f}")
            
            # Trade history
            st.subheader("Recent Trades")
            
            if st.session_state.trades_history:
                df_history = pd.DataFrame(st.session_state.trades_history)
                st.dataframe(df_history, use_container_width=True, hide_index=True)
            else:
                st.info("No trades executed yet")
            
            # Account status
            st.subheader("Account Status")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Status:** {account.status}")
                st.write(f"**Account Type:** {account.account_type}")
            
            with col2:
                st.write(f"**Multiplier:** {account.multiplier}x")
                st.write(f"**Daytrading Buying Power:** ${float(account.daytrading_buying_power):,.2f}")
        
        except Exception as e:
            st.error(f"Error loading performance data: {e}")

# ============================================================================
# FOOTER
# ============================================================================
st.divider()
st.markdown("""
<div style='text-align: center; padding: 20px; color: #888;'>
    <p><strong>Quantum Fox</strong> — AI-Powered Trading Dashboard | Real-time Market Analysis</p>
    <p style='font-size: 12px;'>
        ⚠️ <strong>DISCLAIMER:</strong> This tool is for educational purposes. 
        Trading involves risk. Always use paper mode first. Past performance does not guarantee future results.
    </p>
</div>
""", unsafe_allow_html=True)

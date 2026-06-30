import streamlit as st
import pandas as pd
import plotly.graph_objs as go
import alpaca_trade_api as tradeapi
from datetime import datetime
import os
from dotenv import load_dotenv
import requests
import json

# Load environment variables
load_dotenv()

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="Quantum Fox 🦊 Bot Monitor",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main {
        background-color: #0F1419;
        color: #FFFFFF;
    }
    h1, h2, h3 {
        color: #00D084;
    }
    .stMetric {
        background-color: #1A1F2E;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #00D084;
    }
    .bot-status-active {
        color: #00D084;
        font-weight: bold;
    }
    .bot-status-inactive {
        color: #FF4757;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# INITIALIZATION
# ============================================================================
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'trades_log' not in st.session_state:
    st.session_state.trades_log = []
if 'predictions' not in st.session_state:
    st.session_state.predictions = {}

# ============================================================================
# HEADER
# ============================================================================
st.markdown("""
<div style='background: linear-gradient(135deg, #00D084 0%, #00A86B 100%); padding: 20px; border-radius: 10px; text-align: center;'>
    <h1 style='color: white; margin: 0;'>🦊 Quantum Fox — Bot Monitor</h1>
    <p style='color: white; margin: 5px 0 0 0;'>AI-Powered Autonomous Trading | Real-time Status</p>
</div>
""", unsafe_allow_html=True)

st.markdown("")

# ============================================================================
# SIDEBAR
# ============================================================================
with st.sidebar:
    st.header("⚙️ Bot Configuration")
    
    # API Connection
    st.subheader("Alpaca Connection")
    use_env = st.checkbox("Load from .env", value=True)
    
    if use_env:
        api_key = os.getenv("ALPACA_API_KEY", "")
        api_secret = os.getenv("ALPACA_SECRET_KEY", "")
    else:
        api_key = st.text_input("API Key", type="password")
        api_secret = st.text_input("Secret Key", type="password")
    
    # Bot Settings
    st.subheader("Trading Parameters")
    max_trades = st.number_input("Max Trades/Day", min_value=5, max_value=100, value=30)
    top_stocks = st.number_input("Top Stocks to Trade", min_value=1, max_value=10, value=3)
    position_size = st.slider("Position Size (%)", min_value=1, max_value=20, value=5)
    profit_target = st.slider("Profit Target (%)", min_value=0.1, max_value=5.0, value=0.5, step=0.1)
    stop_loss = st.slider("Stop Loss (%)", min_value=0.1, max_value=5.0, value=0.3, step=0.1)
    
    st.divider()
    
    # Bot Control
    st.subheader("Bot Control")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ START BOT", use_container_width=True):
            st.session_state.bot_running = True
            st.success("✅ Bot started!")
    
    with col2:
        if st.button("⏹️ STOP BOT", use_container_width=True):
            st.session_state.bot_running = False
            st.warning("⏸️ Bot stopped")
    
    # Bot Status
    st.divider()
    st.subheader("Bot Status")
    if st.session_state.bot_running:
        st.markdown('<p class="bot-status-active">🟢 RUNNING</p>', unsafe_allow_html=True)
    else:
        st.markdown('<p class="bot-status-inactive">🔴 STOPPED</p>', unsafe_allow_html=True)
    
    # API Connection Status
    st.subheader("API Status")
    if api_key and api_secret:
        try:
            api = tradeapi.REST(api_key, api_secret, base_url="https://api.alpaca.markets", api_version='v2')
            account = api.get_account()
            st.success("✅ Connected")
            st.metric("Account Status", account.status)
        except Exception as e:
            st.error(f"❌ Error: {str(e)[:50]}")
    else:
        st.warning("⚠️ Enter API credentials")

# ============================================================================
# MAIN DASHBOARD - TABS
# ============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Live Status", "📈 Positions", "📋 Trade Log", "🤖 AI Predictions", "⚙️ Settings"])

# ============================================================================
# TAB 1: LIVE STATUS
# ============================================================================
with tab1:
    if api_key and api_secret:
        try:
            api = tradeapi.REST(api_key, api_secret, base_url="https://api.alpaca.markets", api_version='v2')
            account = api.get_account()
            
            # Key Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Portfolio Value",
                    f"${float(account.equity):,.2f}",
                    delta=f"${float(account.portfolio_value) - float(account.equity):,.2f}"
                )
            
            with col2:
                st.metric("Cash Available", f"${float(account.cash):,.2f}")
            
            with col3:
                st.metric("Buying Power", f"${float(account.buying_power):,.2f}")
            
            with col4:
                st.metric("Account Status", account.status.upper())
            
            # Bot Status Card
            st.divider()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.session_state.bot_running:
                    st.markdown('<p class="bot-status-active">🟢 BOT RUNNING</p>', unsafe_allow_html=True)
                else:
                    st.markdown('<p class="bot-status-inactive">🔴 BOT STOPPED</p>', unsafe_allow_html=True)
            
            with col2:
                st.metric("Trades Today", len(st.session_state.trades_log), f"/{max_trades}")
            
            with col3:
                st.metric("Last Update", datetime.now().strftime("%H:%M:%S"))
            
            # Real-time Trading Activity
            st.subheader("📊 Live Trading Activity")
            
            positions = api.list_positions()
            
            if positions:
                pos_data = []
                total_pl = 0
                
                for pos in positions:
                    pl = float(pos.unrealized_pl)
                    pl_pct = float(pos.unrealized_plpc) * 100
                    total_pl += pl
                    
                    pos_data.append({
                        "Symbol": pos.symbol,
                        "Qty": int(float(pos.qty)),
                        "Entry": f"${float(pos.avg_entry_price):.2f}",
                        "Current": f"${float(pos.current_price):.2f}",
                        "P&L": f"${pl:,.2f}",
                        "P&L %": f"{pl_pct:+.2f}%"
                    })
                
                df_positions = pd.DataFrame(pos_data)
                st.dataframe(df_positions, use_container_width=True, hide_index=True)
                
                st.metric("Total Unrealized P&L", f"${total_pl:,.2f}", delta=f"{(total_pl/float(account.equity)*100):.2f}%")
            else:
                st.info("📭 No open positions")
            
            # Market Status
            st.subheader("📅 Market Status")
            clock = api.get_clock()
            col1, col2 = st.columns(2)
            
            with col1:
                if clock.is_open:
                    st.success("🟢 Market Open")
                else:
                    st.warning("🔴 Market Closed")
            
            with col2:
                st.metric("Current Time (ET)", datetime.now().strftime("%H:%M:%S"))
        
        except Exception as e:
            st.error(f"Error connecting: {e}")
    else:
        st.warning("Please enter API credentials in the sidebar")

# ============================================================================
# TAB 2: POSITIONS
# ============================================================================
with tab2:
    if api_key and api_secret:
        try:
            api = tradeapi.REST(api_key, api_secret, base_url="https://api.alpaca.markets", api_version='v2')
            positions = api.list_positions()
            
            st.subheader("💼 Open Positions")
            
            if positions:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    pos_data = []
                    for pos in positions:
                        pl = float(pos.unrealized_pl)
                        pl_pct = float(pos.unrealized_plpc) * 100
                        
                        pos_data.append({
                            "Symbol": pos.symbol,
                            "Shares": int(float(pos.qty)),
                            "Avg Entry": f"${float(pos.avg_entry_price):.2f}",
                            "Current Price": f"${float(pos.current_price):.2f}",
                            "Market Value": f"${float(pos.market_value):,.2f}",
                            "P&L $": f"${pl:,.2f}",
                            "P&L %": f"{pl_pct:+.2f}%"
                        })
                    
                    df = pd.DataFrame(pos_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                
                with col2:
                    st.subheader("Summary")
                    total_value = sum(float(p.market_value) for p in positions)
                    total_pl = sum(float(p.unrealized_pl) for p in positions)
                    
                    st.metric("Total Market Value", f"${total_value:,.2f}")
                    st.metric("Total P&L", f"${total_pl:,.2f}")
                    st.metric("Open Positions", len(positions))
                
                # Close Position
                st.divider()
                st.subheader("⚠️ Close Position")
                
                symbols = [p.symbol for p in positions]
                close_symbol = st.selectbox("Select Position to Close", symbols)
                
                if st.button("🔒 Close Position", use_container_width=True):
                    try:
                        api.close_position(close_symbol)
                        st.success(f"✅ Position {close_symbol} closed!")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.info("📭 No open positions")
        
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Please enter API credentials")

# ============================================================================
# TAB 3: TRADE LOG
# ============================================================================
with tab3:
    st.subheader("📋 Trade History")
    
    if api_key and api_secret:
        try:
            api = tradeapi.REST(api_key, api_secret, base_url="https://api.alpaca.markets", api_version='v2')
            orders = api.list_orders(status='all', limit=50)
            
            if orders:
                trade_data = []
                for order in reversed(orders):
                    trade_data.append({
                        "Time": order.created_at.strftime("%Y-%m-%d %H:%M:%S") if hasattr(order.created_at, 'strftime') else str(order.created_at)[:19],
                        "Symbol": order.symbol,
                        "Type": order.side.upper(),
                        "Qty": int(float(order.qty)),
                        "Price": f"${float(order.filled_avg_price) if order.filled_avg_price else order.limit_price or 'N/A':.2f}" if order.filled_avg_price or order.limit_price else "N/A",
                        "Status": order.status.upper(),
                        "Filled": int(float(order.filled_qty)) if order.filled_qty else 0
                    })
                
                df_trades = pd.DataFrame(trade_data)
                st.dataframe(df_trades, use_container_width=True, hide_index=True)
                
                # Statistics
                st.divider()
                st.subheader("📊 Today's Statistics")
                
                col1, col2, col3 = st.columns(3)
                
                filled_orders = [o for o in orders if o.status == 'filled']
                
                with col1:
                    st.metric("Total Orders", len(orders))
                
                with col2:
                    st.metric("Filled Orders", len(filled_orders))
                
                with col3:
                    buy_orders = len([o for o in filled_orders if o.side == 'buy'])
                    st.metric("Buy Orders", buy_orders)
            else:
                st.info("📭 No trades today")
        
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Please enter API credentials")

# ============================================================================
# TAB 4: AI PREDICTIONS
# ============================================================================
with tab4:
    st.subheader("🤖 AI Stock Predictions")
    
    st.info("""
    The bot analyzes the top stocks using:
    - SMA Crossover (20 > 50)
    - RSI (Relative Strength Index)
    - MACD (Moving Average Convergence)
    - Bollinger Bands
    - Volume Analysis
    
    Nightly analysis selects the top 3 stocks to trade intraday.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Watched Stocks")
        watched = ["AAPL", "MSFT", "TSLA", "NVDA", "GOOGL", "AMZN", "META", "NFLX", "AMD", "PYPL"]
        for stock in watched[:5]:
            st.write(f"• {stock}")
    
    with col2:
        st.subheader("⏰ Analysis Schedule")
        st.write("**Nightly:** 9:00 PM ET")
        st.write("**Intraday:** Every 15 minutes")
        st.write("**Market Hours:** 9:30 AM - 4:00 PM ET")
    
    st.divider()
    
    st.subheader("📊 Sample Signals")
    
    sample_signals = {
        "AAPL": {"Action": "BUY", "Confidence": 78},
        "MSFT": {"Action": "HOLD", "Confidence": 45},
        "TSLA": {"Action": "SELL", "Confidence": 82}
    }
    
    for stock, signal in sample_signals.items():
        col1, col2, col3 = st.columns([1, 2, 2])
        
        with col1:
            st.write(f"**{stock}**")
        
        with col2:
            st.write(f"Action: {signal['Action']}")
        
        with col3:
            st.progress(signal['Confidence'] / 100, text=f"Confidence: {signal['Confidence']}%")

# ============================================================================
# TAB 5: SETTINGS
# ============================================================================
with tab5:
    st.subheader("⚙️ Bot Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Trading Settings")
        st.write(f"**Max Trades/Day:** {max_trades}")
        st.write(f"**Top Stocks:** {top_stocks}")
        st.write(f"**Position Size:** {position_size}%")
        st.write(f"**Profit Target:** {profit_target}%")
        st.write(f"**Stop Loss:** {stop_loss}%")
    
    with col2:
        st.subheader("Schedule")
        st.write("**Nightly Analysis:** 21:00 ET")
        st.write("**Stock Selection:** Top 3 performers")
        st.write("**Trading Frequency:** Every 15 min")
        st.write("**Market Hours:** 9:30 AM - 4:00 PM ET")
        st.write("**Trading Days:** Mon-Fri")
    
    st.divider()
    
    st.subheader("📋 Running Requirements")
    st.code("""
# Install dependencies
pip install -r requirements.txt

# Run the trading bot
python trading_bot.py

# Run the monitoring dashboard
streamlit run monitor.py
    """)
    
    st.warning("""
    ⚠️ **IMPORTANT:**
    - Bot requires LIVE Alpaca account
    - Must have trading API credentials
    - Real money will be traded
    - Keep .env file secure (never commit to git)
    - Monitor daily P&L closely
    - Adjust parameters based on performance
    """)

# ============================================================================
# FOOTER
# ============================================================================
st.divider()
st.markdown("""
<div style='text-align: center; padding: 20px; color: #888;'>
    <p><strong>Quantum Fox</strong> — Autonomous AI Trading Bot | Real-time Monitor</p>
    <p style='font-size: 12px;'>
        🦊 Trading bot running separately | Monitor displays real-time status
    </p>
</div>
""", unsafe_allow_html=True)

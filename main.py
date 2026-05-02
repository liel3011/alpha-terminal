import os
import time
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import base64
from dotenv import load_dotenv

# --- INTERNAL IMPORTS ---
from core.database import DatabaseManager
try:
    from integrations.discord_listener import DiscordListener
except ImportError as e:
    st.error(f"Missing internal module: {e}")

# --- INITIALIZATION ---
load_dotenv()
st.set_page_config(page_title="Aglo Trader Terminal", layout="wide", page_icon="⚡", initial_sidebar_state="collapsed")
db = DatabaseManager()

# --- HIGH-END PROFESSIONAL CSS (MOBILE OPTIMIZED) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    .stApp { background-color: #090B10; color: #E2E8F0; font-family: 'Inter', sans-serif; }
    header[data-testid="stHeader"], footer { display: none !important; }
    [data-testid="stAppViewBlocker"], div[data-testid="stLoading"] { display: none !important; }
    
    [data-testid="metric-container"] {
        background-color: #121722;
        border: 1px solid #1F2636;
        padding: 10px 15px;
        border-radius: 12px;
    }
    div[data-testid="stMetricValue"] { font-size: 1.3rem !important; color: #10B981; }
    
    .setup-card { 
        background-color: #121722; 
        padding: 20px; 
        border-radius: 14px; 
        margin-bottom: 20px; 
        border: 1px solid #1F2636; 
    }
    
    .tech-box { 
        background: linear-gradient(145deg, #171E2D, #0F131D);
        padding: 15px; 
        border-radius: 10px; 
        font-size: 0.9rem; 
        margin: 12px 0; 
        border-left: 4px solid #3B82F6; 
    }
    
    .journal-row { 
        background-color: #121722; 
        padding: 15px; 
        border-radius: 10px; 
        margin-bottom: 10px; 
        border: 1px solid #1F2636; 
    }
    
    @media (max-width: 768px) {
        .setup-card { padding: 12px; }
        .stMetricValue { font-size: 1rem !important; }
        .journal-row { padding: 10px; }
    }
</style>
""", unsafe_allow_html=True)

# --- DATE FORMATTER ---
def format_date(dt_str):
    try:
        dt = datetime.fromisoformat(dt_str.split('.')[0].replace('Z',''))
        return dt.strftime("%d/%m/%Y %H:%M")
    except: return dt_str

# --- STATE ---
if 'visible_count_breakouts' not in st.session_state: st.session_state.visible_count_breakouts = 3
if 'visible_count_trendlines' not in st.session_state: st.session_state.visible_count_trendlines = 3
if 'visible_count_fibonacci' not in st.session_state: st.session_state.visible_count_fibonacci = 3

# --- FINANCIAL HELPERS ---
@st.cache_data(ttl=60)
def get_market_pulse():
    pulse = {}
    tickers = {"SPY": "S&P 500", "QQQ": "Nasdaq", "^VIX": "Volatility"}
    for t, name in tickers.items():
        try:
            df = yf.Ticker(t).history(period="2d")
            if len(df) >= 2:
                price = df['Close'].iloc[-1]
                prev = df['Close'].iloc[-2]
                pulse[t] = {"name": name, "price": price, "change": ((price/prev)-1)*100}
        except: pass
    return pulse

@st.cache_data(ttl=300)
def get_technical_data(ticker):
    try:
        df = yf.Ticker(ticker).history(period="3mo")
        if len(df) < 20: return None
        price = df['Close'].iloc[-1]
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
        return {"price": price, "ATR": atr, "RSI": rsi, "Vol": (df['Volume'].iloc[-1]/df['Volume'].rolling(20).mean().iloc[-1])}
    except: return None

@st.cache_data(ttl=86400)
def get_upcoming_earnings():
    major = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'AMD', 'JPM', 'DIS']
    res = []
    for t in major:
        try:
            cal = yf.Ticker(t).calendar
            if isinstance(cal, dict) and 'Earnings Date' in cal:
                nxt = min([pd.to_datetime(d).date() for d in cal['Earnings Date'] if pd.to_datetime(d).date() >= datetime.now().date()])
                res.append({"Ticker": t, "Date": nxt.strftime('%Y-%m-%d'), "Days": (nxt - datetime.now().date()).days})
        except: pass
    return pd.DataFrame(res).sort_values(by="Days") if res else pd.DataFrame()

# --- HEADER ---
st.markdown("<h2 style='color: white;'>⚡ AGLO TRADER TERMINAL</h2>", unsafe_allow_html=True)
pulse = get_market_pulse()
if pulse:
    cols = st.columns(len(pulse))
    for i, (t, data) in enumerate(pulse.items()):
        cols[i].metric(data['name'], f"${data['price']:.2f}", f"{data['change']:+.2f}%", delta_color="inverse" if t=="^VIX" else "normal")

if st.button("Sync Channels", use_container_width=True, type="primary"):
    with st.spinner("Syncing..."):
        DiscordListener(os.getenv("DISCORD_TOKEN")).fetch_new_images()
        st.rerun()

# --- TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🚀 Break", "📈 Trend", "📉 Fib", "📅 Earn", "📓 Log"])

def render_tab(cat, state_key):
    risk_mult = st.number_input("ATR Risk", 0.5, 5.0, 2.0, 0.5, key=f"r_{cat}")
    path = f"data/discord_{cat}"
    if os.path.exists(path):
        files = sorted([f for f in os.listdir(path) if f.endswith('.png')], key=lambda x: os.path.getmtime(os.path.join(path, x)), reverse=True)
        unique, seen = [], set()
        for f in files:
            t = f.split('_')[0].upper()
            if t in ["SETUP", "IMAGE", "IMG", "UNKNOWN"] or t not in seen:
                if t not in ["SETUP", "IMAGE", "IMG", "UNKNOWN"]: seen.add(t)
                unique.append((f, t))
        
        for f, orig_t in unique[:st.session_state[state_key]]:
            st.markdown('<div class="setup-card">', unsafe_allow_html=True)
            st.image(os.path.join(path, f), use_container_width=True)
            ticker = st.text_input("Ticker:", value="" if orig_t in ["SETUP", "IMAGE", "IMG", "UNKNOWN"] else orig_t, key=f"ti_{f}").upper()
            data = get_technical_data(ticker) if ticker else None
            if data:
                sl = data['price'] - (data['ATR'] * risk_mult)
                st.markdown(f'<div class="tech-box"><b>{ticker} | ${data["price"]:.2f}</b><br>RSI: {data["RSI"]:.0f} | <span style="color:#EF4444;">SL: ${sl:.2f} (-{((data["price"]-sl)/data["price"])*100:.1f}%)</span></div>', unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                ent = c1.number_input("Entry", value=float(data['price']), key=f"e_{f}")
                stop = c2.number_input("Stop", value=float(sl), key=f"s_{f}")
                if st.button("📝 Log Trade", use_container_width=True, type="primary", key=f"l_{f}"):
                    db.log_trade(ticker, ent, stop, "", os.path.join(path, f))
                    st.success("Logged!")
            else:
                if st.button("📝 Log Image Only", use_container_width=True, key=f"li_{f}"):
                    db.log_trade(ticker if ticker else "SETUP", 0.0, 0.0, "", os.path.join(path, f))
                    st.success("Logged Image!")
            st.markdown('</div>', unsafe_allow_html=True)

with t1: render_tab("breakouts", "visible_count_breakouts")
with t2: render_tab("trendlines", "visible_count_trendlines")
with t3: render_tab("fibonacci", "visible_count_fibonacci")

with t4:
    st.subheader("Upcoming Earnings")
    earn_df = get_upcoming_earnings()
    if not earn_df.empty:
        st.dataframe(earn_df.style.map(lambda x: 'color: #EF4444' if isinstance(x, int) and x <= 7 else '', subset=['Days']), use_container_width=True, hide_index=True)

with t5:
    st.subheader("Log")
    journal = db.get_journal_data()
    if not journal.empty:
        for _, row in journal.iterrows():
            st.markdown('<div class="journal-row">', unsafe_allow_html=True)
            risk = ((row['entry']-row['atr_sl'])/row['entry'])*100 if row['entry']>0 else 0
            st.markdown(f"""
            <div style="margin-bottom:5px;">
                <b style="color:#3B82F6; font-size:1.1rem;">{row['ticker']}</b> 
                <span style="color:#94A3B8; margin-left:10px;">Ent:</span> <b>${row['entry']:.2f}</b>
                <span style="color:#94A3B8; margin-left:10px;">SL:</span> <b style="color:#EF4444;">${row['atr_sl']:.2f}</b> 
                <span style="color:#EF4444; font-size:0.9rem;">({-risk:.1f}%)</span>
            </div>
            """, unsafe_allow_html=True)
            st.caption(f"📅 {format_date(row['timestamp'])}")
            c1, c2 = st.columns(2)
            if c1.toggle("🔍 View Chart", key=f"v_{row['id']}"):
                st.image(base64.b64decode(row['image_data']), use_container_width=True)
            if c2.button("🗑️ Delete", key=f"d_{row['id']}", use_container_width=True):
                db.delete_trade(row['id'])
                st.rerun()
            curr_n = st.text_input("Notes:", value=row['notes'], key=f"n_{row['id']}")
            if curr_n != row['notes']: db.update_notes(row['id'], curr_n)
            st.markdown('</div>', unsafe_allow_html=True)

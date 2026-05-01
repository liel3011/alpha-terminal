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
st.set_page_config(page_title="Alpha Terminal", layout="wide", page_icon="⚡", initial_sidebar_state="collapsed")
db = DatabaseManager()

# --- HIGH-END PROFESSIONAL CSS (MOBILE OPTIMIZED) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    .stApp { background-color: #090B10; color: #E2E8F0; font-family: 'Inter', sans-serif; }
    
    /* Hide Streamlit Default UI Elements */
    header[data-testid="stHeader"], footer { display: none !important; }
    [data-testid="stAppViewBlocker"], div[data-testid="stLoading"] { display: none !important; }
    
    /* Metrics */
    [data-testid="metric-container"] {
        background-color: #121722;
        border: 1px solid #1F2636;
        padding: 10px 15px;
        border-radius: 12px;
    }
    div[data-testid="stMetricValue"] { font-size: 1.3rem !important; color: #10B981; }
    
    /* Cards */
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
    
    /* Journal Fixes */
    .journal-row { 
        background-color: #121722; 
        padding: 15px; 
        border-radius: 10px; 
        margin-bottom: 10px; 
        border: 1px solid #1F2636; 
    }
    
    /* Image Handling for Mobile Zoom */
    .stImage img {
        border-radius: 8px;
        transition: transform 0.2s ease;
    }
    
    /* Custom button style for mobile */
    .stButton button {
        border-radius: 8px !important;
    }

    @media (max-width: 768px) {
        .setup-card { padding: 12px; }
        .stMetricValue { font-size: 1rem !important; }
        .journal-row { padding: 10px; }
        /* Make images fill width on mobile */
        [data-testid="stHorizontalBlock"] { gap: 0 !important; }
        .stImage { width: 100% !important; }
    }
</style>
""", unsafe_allow_html=True)

# --- DATE FORMATTER HELPER ---
def format_datetime_str(dt_str):
    """Parses an ISO format timestamp and returns a user-friendly string."""
    try:
        # Tries to parse assuming full ISO string with timezone (from db)
        dt_obj = datetime.fromisoformat(dt_str.split('+')[0]) # splits on '+' to ignore TZ
        return dt_obj.strftime("%b %d, %Y at %I:%M %p") # e.g., "May 01, 2026 at 11:34 PM"
    except (ValueError, TypeError):
        return dt_str # return the original if it fails for some reason

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
                pct_change = ((price / prev) - 1) * 100
                pulse[t] = {"name": name, "price": price, "change": pct_change}
        except: pass
    return pulse

@st.cache_data(ttl=300)
def get_technical_data(ticker):
    try:
        df = yf.Ticker(ticker).history(period="3mo")
        if len(df) < 20: return None
        price = df['Close'].iloc[-1]
        df['TR'] = df[['High', 'Low', 'Close']].max(axis=1) - df[['High', 'Low', 'Close']].min(axis=1)
        atr = df['TR'].rolling(14).mean().iloc[-1]
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
        vol_ratio = (df['Volume'].iloc[-1] / df['Volume'].rolling(20).mean().iloc[-1])
        return {"price": price, "ATR": atr, "RSI": rsi, "VolRatio": vol_ratio}
    except: return None

@st.cache_data(ttl=86400)
def get_upcoming_earnings():
    major_tickers = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'AMD', 'JPM', 'DIS']
    results = []
    for t in major_tickers:
        try:
            cal = yf.Ticker(t).calendar
            if isinstance(cal, dict) and 'Earnings Date' in cal:
                next_date = min([pd.to_datetime(d).date() for d in cal['Earnings Date'] if pd.to_datetime(d).date() >= datetime.now().date()])
                days_left = (next_date - datetime.now().date()).days
                results.append({"Ticker": t, "Report Date": next_date.strftime('%Y-%m-%d'), "Days Left": days_left})
        except: pass
    return pd.DataFrame(results).sort_values(by="Days Left") if results else pd.DataFrame()

# ==========================================
# HEADER
# ==========================================
st.markdown("<h2 style='color: white; margin-bottom: 15px; font-weight: 700;'>⚡ ALPHA TERMINAL</h2>", unsafe_allow_html=True)

pulse_data = get_market_pulse()
if pulse_data:
    cols = st.columns(len(pulse_data))
    for i, (t, data) in enumerate(pulse_data.items()):
        color = "normal" if data['change'] >= 0 else "inverse"
        if t == "^VIX": color = "inverse" if data['change'] >= 0 else "normal"
        cols[i].metric(data['name'], f"${data['price']:.2f}", f"{data['change']:+.2f}%", delta_color=color)

if st.button("🔄 Sync Channels", use_container_width=True, type="primary"):
    with st.spinner("Syncing..."):
        DiscordListener(os.getenv("DISCORD_TOKEN")).fetch_new_images()
        st.rerun()

st.divider()

# ==========================================
# REUSABLE TAB BUILDER
# ==========================================
def render_setup_tab(category_name, state_key):
    atr_multiplier = st.number_input("Risk Multiplier (ATR)", 0.5, 5.0, 2.0, 0.5, key=f"atr_{category_name}")
    img_dir = os.path.join("data", f"discord_{category_name}")
    if os.path.exists(img_dir):
        files = sorted([f for f in os.listdir(img_dir) if f.endswith('.png')], key=lambda x: os.path.getmtime(os.path.join(img_dir, x)), reverse=True)
        seen = set()
        unique_setups = []
        placeholders = ["SETUP", "IMAGE", "IMG", "UNKNOWN", "EMBED"]
        
        for f in files:
            ticker = f.split('_')[0].upper()
            if ticker in placeholders or ticker not in seen:
                if ticker not in placeholders: seen.add(ticker)
                unique_setups.append((f, ticker))

        for f, original_ticker in unique_setups[:st.session_state[state_key]]:
            full_path = os.path.join(img_dir, f)
            st.markdown(f'<div class="setup-card">', unsafe_allow_html=True)
            
            # Mobile-friendly layout: Image then Info
            st.image(full_path, use_container_width=True)
            
            user_ticker = st.text_input("Ticker:", value="" if original_ticker in placeholders else original_ticker, key=f"t_{f}").upper().strip()
            techs = get_technical_data(user_ticker) if user_ticker else None

            if techs:
                p = techs['price']
                sl = p - (techs['ATR'] * atr_multiplier)
                risk = ((p - sl) / p) * 100
                st.markdown(f"""
                <div class="tech-box">
                    <b>{user_ticker} | ${p:.2f}</b><br>
                    RSI: {techs['RSI']:.0f} | Vol: {techs['VolRatio']:.1f}x<br>
                    <span style="color:#EF4444; font-weight:bold;">Suggested SL: ${sl:.2f} (-{risk:.1f}%)</span>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                ent = c1.number_input("Entry", value=float(p), key=f"e_{f}")
                stop = c2.number_input("Stop", value=float(sl), key=f"s_{f}")
                
                if st.button("📝 Log Trade", use_container_width=True, type="primary", key=f"l_{f}"):
                    db.log_trade(user_ticker, ent, stop, "", full_path) # Logs an empty string for notes
                    st.success("Logged!")
            else:
                st.caption("Enter ticker to load technicals")
            st.markdown('</div>', unsafe_allow_html=True)

        if len(unique_setups) > st.session_state[state_key]:
            if st.button("Load More", use_container_width=True, key=f"m_{category_name}"):
                st.session_state[state_key] += 3
                st.rerun()

# ==========================================
# TABS
# ==========================================
t1, t2, t3, t4, t5 = st.tabs(["🚀 Break", "📈 Trend", "📉 Fib", "📅 Earn", "📓 Journal"])

with t1: render_setup_tab("breakouts", "visible_count_breakouts")
with t2: render_setup_tab("trendlines", "visible_count_trendlines")
with t3: render_setup_tab("fibonacci", "visible_count_fibonacci")
with t4:
    st.subheader("Upcoming Earnings")
    df = get_upcoming_earnings()
    if not df.empty: st.dataframe(df, use_container_width=True, hide_index=True)

with t5:
    st.subheader("Trading Journal")
    journal = db.get_journal_data()
    if not journal.empty:
        for _, row in journal.iterrows():
            st.markdown(f'<div class="journal-row">', unsafe_allow_html=True)
            
            # Risk calculation for display
            risk_pct = 0
            if row['entry'] > 0 and row['atr_sl'] > 0:
                risk_pct = ((row['entry'] - row['atr_sl']) / row['entry']) * 100
            risk_display = f"(-{risk_pct:.1f}%)" if risk_pct > 0 else ""

            # --- Refactored Mobile Trade Display (segmented) ---
            html_trade_info = f"""
            <div style="font-size: 1.1rem; margin-bottom: 6px;">
                <span style="color: #3B82F6; font-weight: bold;">{row['ticker']}</span> 
                <span style="color: #475569; margin: 0 8px;">|</span>
                <span style="color: #94A3B8;">Entry:</span> 
                <span style="color: #E2E8F0; font-weight: bold;">${row['entry']:.2f}</span> 
                <span style="color: #475569; margin: 0 8px;">|</span>
                <span style="color: #94A3B8;">SL:</span> 
                <span style="color: #EF4444; font-weight: bold;">${row['atr_sl']:.2f} <span style="font-size: 0.85em; font-weight: normal;">{risk_display}</span></span>
            </div>
            """
            st.markdown(html_trade_info, unsafe_allow_html=True)
            
            # --- Better Date Formatting ---
            st.caption(f"Logged on: {format_datetime_str(row['timestamp'])}")
            
            # --- IMPROVED MOBILE IMAGE VIEW ---
            c1, c2 = st.columns(2)
            with c1:
                show_img = st.toggle("🔍 View Chart", key=f"show_{row['id']}")
            with c2:
                if st.button("🗑️ Delete", key=f"del_{row['id']}", use_container_width=True):
                    db.delete_trade(row['id'])
                    st.rerun()
            
            if show_img and row.get('image_data'):
                decoded = base64.b64decode(row['image_data'])
                st.image(decoded, use_container_width=True)
                # Quick Download Button was here, now deleted.
                
            # Notes field: now pre-populated with empty string
            st.text_input("Notes:", value=row['notes'], key=f"n_{row['id']}", on_change=lambda r=row['id']: db.update_notes(r, st.session_state[f"n_{r}"]))
            st.markdown('</div>', unsafe_allow_html=True)

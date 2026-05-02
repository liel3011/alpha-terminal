import os
import time
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import base64
import shutil
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

# --- HIGH-END PROFESSIONAL CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* Base Theme */
    .stApp { 
        background-color: #07090E; 
        color: #F1F5F9; 
        font-family: 'Inter', sans-serif;
    }
    
    /* Layout Adjustments */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        max-width: 1400px;
    }
    
    /* Hide Streamlit Clutter */
    header[data-testid="stHeader"], footer { display: none !important; }
    [data-testid="stAppViewBlocker"], div[data-testid="stLoading"] { display: none !important; }
    
    /* Main Title */
    .main-title {
        color: #FFFFFF; 
        margin-bottom: 20px; 
        font-weight: 800; 
        font-size: 2.2rem !important; 
        letter-spacing: -1px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .main-title span { color: #3B82F6; font-size: 1.2rem; font-weight: 600; background: rgba(59,130,246,0.1); padding: 4px 10px; border-radius: 8px; }

    /* Market Metrics */
    [data-testid="metric-container"] {
        background: linear-gradient(145deg, #131C2D, #0B101A);
        border: 1px solid #1E293B;
        padding: 12px 16px !important; 
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
    }
    div[data-testid="stMetricValue"] { font-size: 1.2rem !important; font-weight: 700; color: #10B981; }
    div[data-testid="stMetricLabel"] { font-size: 0.8rem !important; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.5px; }
    
    /* Customizing Streamlit Tabs (No Scrolling) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: #131C2D;
        border-radius: 8px 8px 0 0;
        padding: 0 16px;
        color: #94A3B8;
        border: 1px solid #1E293B;
        border-bottom: none;
        white-space: nowrap;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3B82F6 !important;
        color: white !important;
        font-weight: 600;
        border-color: #3B82F6 !important;
    }
    
    /* Modern Setup Cards */
    .setup-card { 
        background-color: #131C2D; 
        padding: 24px; 
        border-radius: 16px; 
        margin-bottom: 24px; 
        border: 1px solid #1E293B;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
    }
    .setup-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.6);
        border-color: #334155;
    }
    
    /* Tech Box Dashboard Style */
    .tech-box { 
        background: rgba(15, 23, 42, 0.6);
        padding: 16px; 
        border-radius: 12px; 
        margin: 16px 0; 
        border: 1px solid #1E293B;
        border-left: 4px solid #3B82F6; 
        display: flex;
        flex-direction: column;
        gap: 8px;
    }
    .tech-box-header { font-size: 1.1rem; font-weight: 700; color: #F8FAFC; display: flex; justify-content: space-between; border-bottom: 1px solid #1E293B; padding-bottom: 8px; margin-bottom: 4px; }
    .tech-box-row { display: flex; justify-content: space-between; font-size: 0.9rem; color: #CBD5E1; }
    .tech-box-highlight { color: #EF4444; font-weight: 700; font-size: 1rem; }
    
    /* Log Rows */
    .journal-row { 
        background-color: #131C2D; 
        padding: 20px; 
        border-radius: 12px; 
        margin-bottom: 12px; 
        border: 1px solid #1E293B; 
        transition: background-color 0.2s ease;
    }
    .journal-row:hover { background-color: #1A263D; border-color: #334155; }
    
    /* Buttons Enhancements */
    .stButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #3B82F6, #2563EB) !important;
        box-shadow: 0 0 15px rgba(59, 130, 246, 0.4) !important;
        transform: translateY(-1px);
    }
    
    /* Images */
    .stImage img { border-radius: 10px; border: 1px solid #1E293B; }

    /* Inputs */
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: #0F172A !important;
        border-radius: 8px !important;
        color: #F8FAFC !important;
    }

    @media (max-width: 768px) {
        .setup-card { padding: 16px; }
        .journal-row { padding: 16px; }
        .stImage { width: 100% !important; }
        .main-title { font-size: 1.6rem !important; }
        
        /* THIS IS THE FIX: Allow tabs to shrink and wrap so they fit on mobile without scrolling */
        .stTabs [data-baseweb="tab-list"] {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
        }
        .stTabs [data-baseweb="tab"] { 
            padding: 0 8px; 
            font-size: 0.75rem; 
            flex: 1 1 auto;
            text-align: center;
            height: 38px;
        }
    }
</style>
""", unsafe_allow_html=True)

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
st.markdown("<div class='main-title'>⚡ Aglo Trader <span>Terminal</span></div>", unsafe_allow_html=True)

pulse_data = get_market_pulse()
if pulse_data:
    cols = st.columns(len(pulse_data))
    for i, (t, data) in enumerate(pulse_data.items()):
        color = "normal" if data['change'] >= 0 else "inverse"
        if t == "^VIX": color = "inverse" if data['change'] >= 0 else "normal"
        cols[i].metric(data['name'], f"${data['price']:.2f}", f"{data['change']:+.2f}%", delta_color=color)

# --- SYNC BUTTON ---
st.write("") # Tiny spacer
if st.button("Sync Channels", use_container_width=True, type="primary"):
    with st.spinner("Fetching latest setups and cleaning old data..."):
        for cat in ["breakouts", "trendlines", "fibonacci"]:
            folder = os.path.join("data", f"discord_{cat}")
            if os.path.exists(folder):
                shutil.rmtree(folder)
            os.makedirs(folder, exist_ok=True)
            
        DiscordListener(os.getenv("DISCORD_TOKEN")).fetch_new_images()
        st.rerun()

st.divider()

# ==========================================
# REUSABLE TAB BUILDER
# ==========================================
def render_setup_tab(category_name, state_key):
    atr_multiplier = st.number_input("Risk Multiplier (ATR)", 0.5, 5.0, 1.5, 0.5, key=f"atr_{category_name}")
    img_dir = os.path.join("data", f"discord_{category_name}")
    if os.path.exists(img_dir):
        files = sorted([f for f in os.listdir(img_dir) if f.endswith('.png')], 
                       key=lambda x: int(''.join(filter(str.isdigit, x.split('_')[-1]))) if '_' in x else 0, 
                       reverse=True)
        
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
            
            user_ticker = st.text_input("", value="" if original_ticker in placeholders else original_ticker, key=f"t_{f}", label_visibility="collapsed", placeholder="Enter Ticker...").upper().strip()
            
            try:
                raw_id = ''.join(filter(str.isdigit, f.split('_')[-1]))
                ts_val = int(raw_id)
                if ts_val > 10**17:
                    unix_ts = ((ts_val >> 22) + 1420070400000) / 1000
                    setup_time = datetime.fromtimestamp(unix_ts).strftime('%d/%m/%Y %H:%M')
                elif 1000000000 < ts_val < 2500000000:
                    setup_time = datetime.fromtimestamp(ts_val).strftime('%d/%m/%Y %H:%M')
                else:
                    setup_time = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime('%d/%m/%Y %H:%M')
            except:
                setup_time = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime('%d/%m/%Y %H:%M')
            
            st.markdown(f"<div style='color: #64748B; font-size: 0.8rem; margin-bottom: 10px;'>🕒 Identified: {setup_time}</div>", unsafe_allow_html=True)
            
            st.image(full_path, use_container_width=True)
            
            techs = get_technical_data(user_ticker) if user_ticker else None

            if techs:
                p = techs['price']
                sl = p - (techs['ATR'] * atr_multiplier)
                risk = ((p - sl) / p) * 100
                
                rsi_val = techs['RSI']
                rsi_icon = "🟢" if rsi_val < 30 else "🔴" if rsi_val > 70 else "⚪"
                
                vol_val = techs['VolRatio']
                vol_icon = "🔥" if vol_val > 1.5 else "🧊" if vol_val < 0.8 else "📊"
                
                st.markdown(f"""
                <div class="tech-box">
                    <div class="tech-box-header">
                        <span>{user_ticker}</span>
                        <span style="color: #10B981;">${p:.2f}</span>
                    </div>
                    <div class="tech-box-row">
                        <span>{rsi_icon} RSI</span>
                        <span>{rsi_val:.0f}</span>
                    </div>
                    <div class="tech-box-row">
                        <span>{vol_icon} Volume</span>
                        <span>{vol_val:.1f}x</span>
                    </div>
                    <div class="tech-box-row" style="margin-top: 6px; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 6px;">
                        <span>Target Stop Loss</span>
                        <span class="tech-box-highlight">${sl:.2f} (-{risk:.1f}%)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                ent = c1.number_input("Entry Price", value=float(p), key=f"e_{f}")
                stop = c2.number_input("Stop Loss", value=float(sl), key=f"s_{f}")
                
                if st.button("📝 Log Trade", use_container_width=True, type="primary", key=f"l_{f}"):
                    db.log_trade(user_ticker, ent, stop, "", full_path)
                    st.success("Successfully Logged!")
            else:
                st.caption("Waiting for valid ticker symbol to fetch technical data...")
            st.markdown('</div>', unsafe_allow_html=True)

        if len(unique_setups) > st.session_state[state_key]:
            if st.button("Load More Setups", use_container_width=True, key=f"m_{category_name}"):
                st.session_state[state_key] += 3
                st.rerun()

# ==========================================
# TABS (Shortened for Mobile)
# ==========================================
t1, t2, t3, t4, t5 = st.tabs(["🚀 Break", "📈 Trend", "📉 Fib", "📅 Earn", "📓 Log"])

with t1: render_setup_tab("breakouts", "visible_count_breakouts")
with t2: render_setup_tab("trendlines", "visible_count_trendlines")
with t3: render_setup_tab("fibonacci", "visible_count_fibonacci")

with t4:
    df = get_upcoming_earnings()
    if not df.empty:
        def style_days(val):
            if val <= 3: color = '#EF4444' 
            elif val <= 7: color = '#F59E0B' 
            else: color = '#10B981' 
            return f'color: {color}; font-weight: 700;'

        df_display = df.copy()
        df_display.columns = ["Ticker", "📅 Report Date", "⏳ Days Left"]
        
        st.dataframe(
            df_display.style.map(style_days, subset=['⏳ Days Left']),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No earnings reports found for major tickers.")

with t5:
    st.subheader("Interactive Trading Log")
    log_data = db.get_journal_data()
    if not log_data.empty:
        for _, row in log_data.iterrows():
            st.markdown(f'<div class="journal-row">', unsafe_allow_html=True)
            risk = ((row['entry'] - row['atr_sl']) / row['entry']) * 100 if row['entry'] > 0 else 0
            
            html_info = f"""
            <div style='display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; margin-bottom: 12px;'>
                <div style='display: flex; align-items: center; gap: 12px;'>
                    <span style='color:#3B82F6; font-size: 1.3rem; font-weight: 800;'>{row['ticker']}</span>
                    <span style='color:#475569;'>|</span>
                    <span style='font-size: 1rem; color: #E2E8F0;'>Ent: <b>${row['entry']:.2f}</b></span>
                    <span style='color:#475569;'>|</span>
                    <span style='font-size: 1rem; color: #E2E8F0;'>SL: <b style='color:#EF4444;'>${row['atr_sl']:.2f}</b> <span style='font-size: 0.85rem; color:#EF4444;'>(-{risk:.1f}%)</span></span>
                </div>
            </div>
            """
            st.markdown(html_info, unsafe_allow_html=True)
            
            try:
                clean_date = pd.to_datetime(row['timestamp']).strftime('%d/%m/%Y %H:%M')
            except:
                clean_date = row['timestamp']
            st.markdown(f"<div style='color: #64748B; font-size: 0.8rem; margin-bottom: 15px;'>📅 Logged on: {clean_date}</div>", unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1: show_img = st.toggle("🔍 View Chart", key=f"show_{row['id']}")
            with c2:
                if st.button("🗑️ Delete", key=f"del_{row['id']}", use_container_width=True):
                    db.delete_trade(row['id'])
                    st.rerun()
            
            if show_img and row.get('image_data'):
                decoded = base64.b64decode(row['image_data'])
                st.image(decoded, use_container_width=True)
            
            current_note = row['notes']
            if current_note and current_note.startswith("Category:"):
                current_note = ""
                
            st.text_input("Notes:", value=current_note, key=f"n_{row['id']}", placeholder="Add your reflections or exit notes...", on_change=lambda r=row['id']: db.update_notes(r, st.session_state[f"n_{r}"]))
            st.markdown('</div>', unsafe_allow_html=True)

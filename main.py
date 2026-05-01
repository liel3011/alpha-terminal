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

# --- HARDCORE MOBILE & SPACE OPTIMIZATION CSS ---
st.markdown("""
<style>
    /* 1. אופטימיזציה של המרווח העליון - דחיפה לקצה */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0.7rem !important;
        padding-right: 0.7rem !important;
    }
    
    /* 2. העלמת אלמנטים מיותרים שתופסים מקום */
    header[data-testid="stHeader"], footer { height: 0px !important; display: none !important; }
    [data-testid="stAppViewBlocker"] { display: none !important; }
    
    /* 3. עיצוב כללי וצבעים */
    .stApp { background-color: #090B10; color: #E2E8F0; font-family: 'Inter', sans-serif; }
    
    /* 4. צמצום מרווחים בין אלמנטים (Gap reduction) */
    div[data-testid="stVerticalBlock"] > div { margin-top: -0.5rem !important; }
    
    /* 5. כרטיסיות נקיות יותר לטלפון */
    .setup-card { 
        background-color: #121722; 
        padding: 10px; 
        border-radius: 10px; 
        margin-bottom: 15px; 
        border: 1px solid #1F2636; 
    }
    
    /* 6. תיקון תצוגת תמונה - מקסימום רוחב ללא שוליים */
    .stImage > div > img {
        border-radius: 6px;
        width: 100% !important;
    }

    /* 7. כיווץ הטאבים שייכנסו בשורה אחת */
    .stTabs [data-baseweb="tab-list"] { gap: 2px; }
    .stTabs [data-baseweb="tab"] { 
        padding-left: 8px; 
        padding-right: 8px; 
        font-size: 14px; 
    }

    @media (max-width: 768px) {
        h2 { font-size: 1.4rem !important; margin-top: -10px !important; }
        .tech-box { padding: 10px; font-size: 0.85rem; }
        [data-testid="metric-container"] { padding: 5px 10px; }
    }
</style>
""", unsafe_allow_html=True)

# --- STATE ---
if 'visible_count_breakouts' not in st.session_state: st.session_state.visible_count_breakouts = 3
if 'visible_count_trendlines' not in st.session_state: st.session_state.visible_count_trendlines = 3
if 'visible_count_fibonacci' not in st.session_state: st.session_state.visible_count_fibonacci = 3

# --- HELPERS ---
@st.cache_data(ttl=60)
def get_market_pulse():
    pulse = {}
    for t, name in {"SPY": "S&P 500", "QQQ": "Nasdaq", "^VIX": "VIX"}.items():
        try:
            df = yf.Ticker(t).history(period="2d")
            p, prev = df['Close'].iloc[-1], df['Close'].iloc[-2]
            pulse[t] = {"name": name, "price": p, "change": ((p/prev)-1)*100}
        except: pass
    return pulse

@st.cache_data(ttl=300)
def get_technical_data(ticker):
    try:
        df = yf.Ticker(ticker).history(period="3mo")
        p = df['Close'].iloc[-1]
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        return {"price": p, "ATR": atr}
    except: return None

# ==========================================
# MAIN UI
# ==========================================
st.markdown("<h2 style='color: white; margin-bottom: 5px;'>⚡ ALPHA <span style='color:#3B82F6'>PRO</span></h2>", unsafe_allow_html=True)

# שורת מדדים קומפקטית
pulse_data = get_market_pulse()
if pulse_data:
    cols = st.columns(len(pulse_data))
    for i, (t, data) in enumerate(pulse_data.items()):
        cols[i].metric(data['name'], f"${data['price']:.1f}", f"{data['change']:+.1f}%", delta_color="inverse" if t=="^VIX" else "normal")

if st.button("🔄 Sync", use_container_width=True):
    DiscordListener(os.getenv("DISCORD_TOKEN")).fetch_new_images()
    st.rerun()

# --- TABS ---
t1, t2, t3, t4, t5 = st.tabs(["🚀Brk", "📈Trnd", "📉Fib", "📅Earn", "📓Jrn"])

def render_tab(cat, state_key):
    path = f"data/discord_{cat}"
    if os.path.exists(path):
        files = [f for f in os.listdir(path) if f.endswith('.png')]
        for f in files[:st.session_state[state_key]]:
            ticker = f.split('_')[0].upper()
            st.markdown('<div class="setup-card">', unsafe_allow_html=True)
            st.image(os.path.join(path, f), use_container_width=True)
            
            u_tick = st.text_input("Ticker:", value="" if ticker in ["SETUP","IMAGE"] else ticker, key=f"i_{f}").upper()
            if u_tick:
                data = get_technical_data(u_tick)
                if data:
                    sl = data['price'] - (data['ATR'] * 2)
                    st.caption(f"Price: ${data['price']:.2f} | SL: ${sl:.2f}")
                    if st.button("Log", key=f"b_{f}", use_container_width=True):
                        db.log_trade(u_tick, data['price'], sl, cat, os.path.join(path, f))
                        st.toast("Saved!")
            st.markdown('</div>', unsafe_allow_html=True)
        if len(files) > st.session_state[state_key]:
            if st.button("More", key=f"m_{cat}", use_container_width=True):
                st.session_state[state_key] += 3; st.rerun()

with t1: render_tab("breakouts", "visible_count_breakouts")
with t2: render_tab("trendlines", "visible_count_trendlines")
with t3: render_tab("fibonacci", "visible_count_fibonacci")
with t5:
    journal = db.get_journal_data()
    if not journal.empty:
        for _, row in journal.iterrows():
            st.markdown('<div class="journal-row">', unsafe_allow_html=True)
            st.markdown(f"**{row['ticker']}** | ${row['entry']:.2f}", unsafe_allow_html=True)
            if st.toggle("Chart", key=f"v_{row['id']}"):
                img = base64.b64decode(row['image_data'])
                st.image(img, use_container_width=True)
                st.download_button("Save", img, f"{row['ticker']}.png", "image/png", use_container_width=True)
            if st.button("Del", key=f"d_{row['id']}", use_container_width=True):
                db.delete_trade(row['id']); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

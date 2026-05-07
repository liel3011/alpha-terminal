import os
import time
import sqlite3
import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import base64
import shutil
from dotenv import load_dotenv

from core.database import DatabaseManager

try:
    from integrations.discord_listener import DiscordListener
except ImportError as e:
    st.error(f"Missing internal module: {e}")

load_dotenv()
st.set_page_config(page_title="Aglo Trader Terminal", layout="wide", page_icon="🪙", initial_sidebar_state="collapsed")
db = DatabaseManager()

def update_trade_data_supabase(db_instance, trade_id, new_entry, new_sl):
    try:
        db_instance.supabase.table("trades").update({
            "entry": float(new_entry),
            "atr_sl": float(new_sl)
        }).eq("id", trade_id).execute()
    except Exception as e:
        st.error(f"Database error: {e}")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    .stApp { 
        background-color: #09090B; 
        color: #FAFAFA; 
        font-family: 'Inter', sans-serif;
    }
    
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 1200px;
    }
    
    header[data-testid="stHeader"], footer { display: none !important; }
    [data-testid="stAppViewBlocker"], div[data-testid="stLoading"] { display: none !important; }
    
    .main-title {
        color: #FFFFFF; 
        margin-bottom: 16px; 
        font-weight: 800; 
        font-size: 2rem !important; 
        letter-spacing: -0.5px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .main-title span { 
        color: #3B82F6; 
        font-size: 1.1rem; 
        font-weight: 600; 
        background: rgba(59,130,246,0.15); 
        padding: 4px 12px; 
        border-radius: 6px; 
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
        border-bottom: 1px solid #27272A;
        padding-bottom: 0;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        background-color: transparent;
        border-radius: 0;
        padding: 0 16px;
        color: #A1A1AA;
        border: none;
        border-bottom: 2px solid transparent;
        white-space: nowrap;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: transparent !important;
        color: #FAFAFA !important;
        font-weight: 600;
        border-bottom: 2px solid #3B82F6 !important;
    }
    
    .stTabs .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        border-bottom: none;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    
    .stTabs .stTabs [data-baseweb="tab"] {
        height: 32px;
        padding: 0 14px;
        font-size: 0.85rem;
        background-color: #18181B;
        border-radius: 16px;
        border: 1px solid #27272A;
    }
    
    .stTabs .stTabs [aria-selected="true"] {
        background-color: #2563EB !important;
        border-color: #2563EB !important;
        color: #FFFFFF !important;
    }
    
    .setup-card { 
        background-color: #18181B; 
        padding: 20px; 
        border-radius: 12px; 
        margin-bottom: 20px; 
        border: 1px solid #27272A;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    .tech-box { 
        background-color: #09090B;
        padding: 14px; 
        border-radius: 8px; 
        margin: 14px 0; 
        border: 1px solid #27272A;
        border-left: 3px solid #3B82F6; 
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    
    .tech-box-header { 
        font-size: 1.05rem; 
        font-weight: 700; 
        color: #FAFAFA; 
        display: flex; 
        justify-content: space-between; 
        border-bottom: 1px solid #27272A; 
        padding-bottom: 6px; 
        margin-bottom: 2px; 
    }
    
    .tech-box-row { 
        display: flex; 
        justify-content: space-between; 
        font-size: 0.85rem; 
        color: #A1A1AA; 
    }
    
    .tech-box-highlight { 
        color: #EF4444; 
        font-weight: 600; 
    }
    
    .journal-row { 
        background-color: #18181B; 
        padding: 16px 20px; 
        border-radius: 12px; 
        margin-bottom: 12px; 
        border: 1px solid #27272A; 
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        border: 1px solid #3F3F46 !important;
        background-color: #18181B !important;
        color: #FAFAFA !important;
        transition: all 0.15s ease !important;
    }
    
    .stButton > button[kind="primary"] {
        background-color: #2563EB !important;
        border: 1px solid #2563EB !important;
        color: #FFFFFF !important;
    }
    
    .stButton > button:hover {
        border-color: #52525B !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        background-color: #1D4ED8 !important;
        border-color: #1D4ED8 !important;
    }
    
    .stImage img { 
        border-radius: 8px; 
        border: 1px solid #27272A; 
    }

    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: #09090B !important;
        border-radius: 6px !important;
        color: #FAFAFA !important;
        border: 1px solid #27272A !important;
        padding: 8px 12px !important;
    }
    
    .stTextInput>div>div>input:focus, .stNumberInput>div>div>input:focus {
        border-color: #3B82F6 !important;
        box-shadow: none !important;
    }

    .discord-msg-box {
        background-color: rgba(39, 39, 42, 0.4);
        border-left: 3px solid #52525B;
        padding: 10px 14px;
        border-radius: 0 6px 6px 0;
        margin-bottom: 14px;
        font-size: 0.85rem;
        color: #D4D4D8;
        line-height: 1.4;
    }

    div[data-testid="stExpander"] {
        background-color: #18181B !important;
        border: 1px solid #27272A !important;
        border-radius: 8px !important;
        margin-top: 8px;
    }
    
    div[data-testid="stExpander"] summary {
        background-color: transparent !important;
    }

    div[role="radiogroup"] {
        display: flex !important;
        flex-wrap: nowrap !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        gap: 12px !important;
        padding-bottom: 8px !important;
    }
    div[role="radiogroup"] label {
        white-space: nowrap !important;
        min-width: fit-content !important;
    }
    div[role="radiogroup"] label p {
        white-space: nowrap !important;
        margin: 0 !important;
        font-size: 0.85rem;
        color: #A1A1AA;
    }
    div[role="radiogroup"]::-webkit-scrollbar {
        height: 0px; 
        background: transparent;
    }
    
    .data-pill {
        background-color: #27272A;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        color: #E4E4E7;
        display: inline-flex;
        align-items: center;
    }
    .data-pill b {
        color: #FAFAFA;
        margin-left: 4px;
    }

    @media (max-width: 768px) {
        .setup-card { padding: 14px; }
        .journal-row { padding: 14px; }
        .stImage { width: 100% !important; }
        .main-title { font-size: 1.5rem !important; }
        
        .stTabs [data-baseweb="tab-list"] {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-start;
        }
        
        .stTabs [data-baseweb="tab"] { 
            padding: 0 10px; 
            font-size: 0.8rem; 
            flex: 1 1 auto;
            text-align: center;
            height: 36px;
        }
    }
</style>
""", unsafe_allow_html=True)

if 'visible_count_breakouts' not in st.session_state: st.session_state.visible_count_breakouts = 5
if 'visible_count_trendlines' not in st.session_state: st.session_state.visible_count_trendlines = 5
if 'visible_count_fibonacci' not in st.session_state: st.session_state.visible_count_fibonacci = 5

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

@st.cache_data(ttl=3600)
def get_stock_info(ticker):
    try:
        return yf.Ticker(ticker).info
    except:
        return {}

@st.cache_data(ttl=3600)
def get_upcoming_earnings():
    major_tickers = [
        'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'AMD', 'JPM', 'DIS',
        'PLTR', 'ARM', 'SMCI', 'MU', 'INTC', 'SNOW', 'CRWD', 'UBER', 'COIN', 'SOFI', 'ROKU',
        'PYPL', 'HOOD', 'BA', 'MSTR', 'MARA', 'RIOT', 'SQ', 'SHOP', 'SPOT', 'CRM', 'ABNB', 'CVNA', 'RBLX'
    ]
    results = []
    for t in major_tickers:
        try:
            tkr = yf.Ticker(t)
            cal = tkr.calendar
            dates = []
            
            if isinstance(cal, pd.DataFrame) and not cal.empty:
                if 'Earnings Date' in cal.columns:
                    dates = pd.to_datetime(cal['Earnings Date']).dt.date.tolist()
                elif isinstance(cal.index, pd.DatetimeIndex):
                    dates = cal.index.date.tolist()
            elif isinstance(cal, dict) and 'Earnings Date' in cal:
                raw_dates = cal['Earnings Date']
                if not isinstance(raw_dates, list): raw_dates = [raw_dates]
                dates = [pd.to_datetime(d).date() for d in raw_dates]
                
            future_dates = [d for d in dates if d >= datetime.now().date()]
            
            if future_dates:
                next_date = min(future_dates)
                days_left = (next_date - datetime.now().date()).days
                
                sentiment = "-"
                
                if days_left <= 21:
                    score = 50 
                    try:
                        info = tkr.info
                        
                        curr_p = info.get('currentPrice') or info.get('previousClose') or 0
                        targ_p = info.get('targetMeanPrice', 0)
                        if curr_p > 0 and targ_p > 0:
                            upside = ((targ_p - curr_p) / curr_p) * 100
                            if upside > 20: score += 10
                            elif upside > 5: score += 5
                            elif upside < -5: score -= 10
                            elif upside < -15: score -= 20

                        try:
                            ed = tkr.earnings_dates
                            if ed is not None and not ed.empty and 'Surprise(%)' in ed.columns:
                                past_ed = ed[ed.index < pd.Timestamp.now(tz='UTC')].head(4)
                                if not past_ed.empty:
                                    avg_surp = past_ed['Surprise(%)'].mean()
                                    if avg_surp > 0.15: score += 10
                                    elif avg_surp > 0.05: score += 5
                                    elif avg_surp < 0: score -= 15
                        except: pass

                        ma50 = info.get('fiftyDayAverage', 0)
                        if curr_p > 0 and ma50 > 0:
                            if curr_p > ma50: score += 5
                            else: score -= 15
                            
                        short_pct = info.get('shortPercentOfFloat', 0)
                        if short_pct and short_pct > 0.08:
                            score += 10

                        try:
                            exps = tkr.options
                            if exps:
                                opt = tkr.option_chain(exps[0])
                                calls_oi = opt.calls['openInterest'].sum() if 'openInterest' in opt.calls else 0
                                puts_oi = opt.puts['openInterest'].sum() if 'openInterest' in opt.puts else 0
                                if calls_oi > 0:
                                    pc_ratio = puts_oi / calls_oi
                                    if pc_ratio > 1.0: score -= 20
                                    elif pc_ratio > 0.8: score -= 10
                                    elif pc_ratio < 0.4: score += 10
                        except: pass

                        try:
                            insiders = tkr.insider_transactions
                            if insiders is not None and not insiders.empty:
                                if 'Shares' in insiders.columns:
                                    net_shares = insiders.head(15)['Shares'].sum()
                                    if net_shares > 10000: score += 10
                                    elif net_shares < -10000: score -= 10
                        except: pass

                        score = max(0, min(100, int(score)))

                        if score >= 80:
                            sentiment = f"🔥 High Beat Prob ({score}%)"
                        elif score >= 60:
                            sentiment = f"🟢 Likely Beat ({score}%)"
                        elif score >= 40:
                            sentiment = f"⚪ Mixed ({score}%)"
                        else:
                            sentiment = f"🔴 High Miss Risk ({score}%)"

                    except:
                        sentiment = "⚪ Neutral (Data missing)"
                    
                results.append({
                    "Ticker": t, 
                    "Report Date": next_date.strftime('%Y-%m-%d'), 
                    "Days Left": days_left,
                    "Prediction": sentiment
                })
        except: pass
    return pd.DataFrame(results).sort_values(by="Days Left") if results else pd.DataFrame()

def render_stock_deep_dive(ticker, key_prefix):
    if not ticker: return
    try:
        c_time, c_ref = st.columns([4, 1])
        with c_time:
            timeframe = st.radio("", ["1d", "5d", "1mo", "3mo", "6mo", "1y", "ytd"], horizontal=True, key=f"tf_{key_prefix}", label_visibility="collapsed")
        with c_ref:
            if st.button("🔄 Refresh", key=f"ref_{key_prefix}", use_container_width=True):
                st.rerun()

        tkr = yf.Ticker(ticker)
        info = get_stock_info(ticker)
        
        if timeframe == "1d":
            hist_df = tkr.history(period="1d", interval="2m")
        else:
            hist_df = tkr.history(period=timeframe)
        
        if not hist_df.empty:
            live_data = tkr.history(period="1d", interval="1m")
            if not live_data.empty:
                current_price = live_data['Close'].iloc[-1]
            else:
                current_price = hist_df['Close'].iloc[-1]
                
            if timeframe == "1d" and info.get('previousClose'):
                start_price = info.get('previousClose')
            else:
                start_price = hist_df['Close'].iloc[0]
                
            diff = current_price - start_price
            pct_diff = (diff / start_price) * 100
            
            color = "#10B981" if diff >= 0 else "#EF4444"
            sign = "+" if diff >= 0 else ""
            
            st.markdown(f"""
            <div style='margin-bottom: 15px; margin-top: 5px;'>
                <span style='font-size: 2.2rem; font-weight: 800; color: #FAFAFA; letter-spacing: -1px;'>${current_price:.2f}</span>
                <span style='color: {color}; font-size: 1.1rem; font-weight: 600; margin-left: 12px;'>
                    {sign}{diff:.2f} ({sign}{pct_diff:.2f}%)
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            mcap = info.get('marketCap', 0)
            pe = info.get('trailingPE', 'N/A')
            high52 = info.get('fiftyTwoWeekHigh', 'N/A')
            low52 = info.get('fiftyTwoWeekLow', 'N/A')
            
            def format_num(val):
                if val == 'N/A' or not val: return "N/A"
                if val >= 1e12: return f"${val/1e12:.2f}T"
                if val >= 1e9: return f"${val/1e9:.2f}B"
                if val >= 1e6: return f"${val/1e6:.2f}M"
                return str(val)
            
            pe_str = f"{pe:.2f}" if isinstance(pe, (int, float)) else "N/A"
            high52_str = f"${high52:.2f}" if high52 != 'N/A' else "N/A"
            low52_str = f"${low52:.2f}" if low52 != 'N/A' else "N/A"
            
            st.markdown(f"""
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; background: rgba(15, 23, 42, 0.4); padding: 12px; border-radius: 8px; border: 1px solid #1E293B;">
                <div><div style="color:#64748B; font-size:0.65rem; font-weight:700;">MKT CAP</div><div style="font-size:0.9rem; font-weight:600; color:#E2E8F0;">{format_num(mcap)}</div></div>
                <div><div style="color:#64748B; font-size:0.65rem; font-weight:700;">P/E</div><div style="font-size:0.9rem; font-weight:600; color:#E2E8F0;">{pe_str}</div></div>
                <div><div style="color:#64748B; font-size:0.65rem; font-weight:700;">52W HIGH</div><div style="font-size:0.9rem; font-weight:600; color:#E2E8F0;">{high52_str}</div></div>
                <div><div style="color:#64748B; font-size:0.65rem; font-weight:700;">52W LOW</div><div style="font-size:0.9rem; font-weight:600; color:#E2E8F0;">{low52_str}</div></div>
            </div>
            """, unsafe_allow_html=True)
            
        else:
            st.warning("No historical data available for this timeframe.")
    except Exception as e:
        st.caption("Detailed info unavailable at the moment.")

st.markdown("<div class='main-title'>🪙 Aglo Trader <span>Terminal</span></div>", unsafe_allow_html=True)

pulse_data = get_market_pulse()
if pulse_data:
    pulse_html = "<div style='display: flex; gap: 12px; margin-bottom: 24px; overflow-x: auto; padding-bottom: 4px;'>"
    for t, data in pulse_data.items():
        is_pos = data['change'] >= 0
        c = "#EF4444" if (t == "^VIX" and is_pos) or (t != "^VIX" and not is_pos) else "#10B981"
        s = "+" if data['change'] >= 0 else ""
        pulse_html += f"<div style='flex: 1; min-width: 100px; background-color: #18181B; border: 1px solid #27272A; border-radius: 12px; padding: 12px; text-align: center;'><div style='color: #A1A1AA; font-size: 0.7rem; font-weight: 700; text-transform: uppercase;'>{data['name']}</div><div style='color: #FAFAFA; font-size: 1.15rem; font-weight: 800; margin: 4px 0;'>${data['price']:.2f}</div><div style='color: {c}; font-size: 0.8rem; font-weight: 600;'>{s}{data['change']:.2f}%</div></div>"
    pulse_html += "</div>"
    st.markdown(pulse_html, unsafe_allow_html=True)

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
            
            st.markdown(f"<div style='color: #A1A1AA; font-size: 0.75rem; margin-bottom: 8px; font-weight: 500;'>🕒 Identified: {setup_time}</div>", unsafe_allow_html=True)
            
            base_filename = os.path.splitext(f)[0]
            txt_filepath = os.path.join(img_dir, f"{base_filename}.txt")
            discord_msg = ""
            if os.path.exists(txt_filepath):
                try:
                    with open(txt_filepath, "r", encoding="utf-8") as txt_file:
                        discord_msg = txt_file.read().strip()
                except Exception:
                    pass
                    
            if discord_msg:
                st.markdown(f"<div class='discord-msg-box'>💬 <i>{discord_msg}</i></div>", unsafe_allow_html=True)
            
            st.image(full_path, use_container_width=True)
            
            techs = get_technical_data(user_ticker) if user_ticker else None

            if techs:
                p = techs['price']
                sl_base = p - (techs['ATR'] * atr_multiplier)
                risk_base = ((p - sl_base) / p) * 100
                
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
                    <div class="tech-box-row" style="margin-top: 4px; border-top: 1px solid #27272A; padding-top: 6px;">
                        <span>Target SL</span>
                        <span class="tech-box-highlight">${sl_base:.2f} (-{risk_base:.1f}%)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander("📊 Advanced Data"):
                    render_stock_deep_dive(user_ticker, f"card_{f}")
                
                with st.expander("⚙️ Execute Trade"):
                    c1, c2 = st.columns([1, 1])
                    ent = c1.number_input("Entry Price", value=float(p), key=f"e_{f}")
                    qty = c2.number_input("Quantity", min_value=1.0, value=10.0, step=1.0, key=f"q_{f}")
                    
                    sl_type = st.radio("Stop Loss Type", ["Percentage (%)", "Price ($)"], horizontal=True, key=f"sl_type_{f}")
                    
                    if sl_type == "Percentage (%)":
                        sl_pct = st.number_input("Stop Loss (%)", min_value=0.1, max_value=99.0, value=float(f"{risk_base:.1f}"), step=0.5, key=f"sl_pct_{f}")
                        stop = ent * (1 - (sl_pct / 100))
                        st.caption(f"Calculated SL Price: ${stop:.2f}")
                    else:
                        stop = st.number_input("Stop Loss ($)", value=float(sl_base), key=f"s_{f}")
                    
                    if st.button("📝 Log Trade", use_container_width=True, type="primary", key=f"l_{f}"):
                        note_str = f"QTY:{qty}|"
                        db.log_trade(user_ticker, ent, stop, note_str, full_path)
                        st.success("Successfully Logged!")
            else:
                st.caption("Waiting for valid ticker symbol...")
            st.markdown('</div>', unsafe_allow_html=True)

        if len(unique_setups) > st.session_state[state_key]:
            if st.button("Load More Setups", use_container_width=True, key=f"m_{category_name}"):
                st.session_state[state_key] += 5
                st.rerun()

main_tab1, main_tab2, main_tab3 = st.tabs(["📊 Scanners", "📅 Earn", "📓 Log"])

with main_tab1:
    t1, t2, t3 = st.tabs(["🚀 Break", "📈 Trend", "📉 Fib"])
    
    with t1: render_setup_tab("breakouts", "visible_count_breakouts")
    with t2: render_setup_tab("trendlines", "visible_count_trendlines")
    with t3: render_setup_tab("fibonacci", "visible_count_fibonacci")

with main_tab2:
    df = get_upcoming_earnings()
    if not df.empty:
        def style_days(val):
            if val <= 3: color = '#EF4444' 
            elif val <= 7: color = '#F59E0B' 
            else: color = '#10B981' 
            return f'color: {color}; font-weight: 700;'

        df_display = df.copy()
        df_display.columns = ["Ticker", "📅 Report Date", "⏳ Days Left", "📊 Prediction"]
        
        st.dataframe(
            df_display.style.map(style_days, subset=['⏳ Days Left']),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No upcoming earnings found.")

with main_tab3:
    show_manual = st.toggle("➕ Add Manual Trade")
    if show_manual:
        c_tick, c_atr = st.columns([2, 1])
        man_ticker = c_tick.text_input("Enter Ticker Symbol:", key="man_ticker", placeholder="e.g. AAPL...").upper().strip()
        man_atr_mult = c_atr.number_input("Risk Multiplier (ATR)", 0.5, 5.0, 1.5, 0.5, key="man_atr_mult")
        
        if man_ticker:
            man_techs = get_technical_data(man_ticker)
            if man_techs:
                man_p = man_techs['price']
                man_sl_base = man_p - (man_techs['ATR'] * man_atr_mult)
                man_risk_base = ((man_p - man_sl_base) / man_p) * 100
                
                rsi_val = man_techs['RSI']
                rsi_icon = "🟢" if rsi_val < 30 else "🔴" if rsi_val > 70 else "⚪"
                vol_val = man_techs['VolRatio']
                vol_icon = "🔥" if vol_val > 1.5 else "🧊" if vol_val < 0.8 else "📊"
                
                st.markdown(f"""
                <div class="tech-box">
                    <div class="tech-box-header">
                        <span>{man_ticker}</span>
                        <span style="color: #10B981;">${man_p:.2f}</span>
                    </div>
                    <div class="tech-box-row">
                        <span>{rsi_icon} RSI</span>
                        <span>{rsi_val:.0f}</span>
                    </div>
                    <div class="tech-box-row">
                        <span>{vol_icon} Volume</span>
                        <span>{vol_val:.1f}x</span>
                    </div>
                    <div class="tech-box-row" style="margin-top: 4px; border-top: 1px solid #27272A; padding-top: 6px;">
                        <span>Target SL</span>
                        <span class="tech-box-highlight">${man_sl_base:.2f} (-{man_risk_base:.1f}%)</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander("📊 Advanced Data"):
                    render_stock_deep_dive(man_ticker, "man_dd")
                
                with st.expander("⚙️ Execute Trade"):
                    mc1, mc2 = st.columns([1, 1])
                    man_ent = mc1.number_input("Entry Price", value=float(man_p), key="man_e")
                    man_qty = mc2.number_input("Quantity", min_value=1.0, value=10.0, step=1.0, key="man_q")
                    
                    sl_type = st.radio("Stop Loss Type", ["Percentage (%)", "Price ($)"], horizontal=True, key="man_sl_type")
                    
                    if sl_type == "Percentage (%)":
                        man_sl_pct = st.number_input("Stop Loss (%)", min_value=0.1, max_value=99.0, value=float(f"{man_risk_base:.1f}"), step=0.5, key="man_sl_pct")
                        man_stop = man_ent * (1 - (man_sl_pct / 100))
                        st.caption(f"Calculated SL Price: ${man_stop:.2f}")
                    else:
                        man_stop = st.number_input("Stop Loss ($)", value=float(man_sl_base), key="man_s")
                    
                    if st.button("📝 Log Manual Trade", use_container_width=True, type="primary", key="man_log_btn"):
                        note_str = f"QTY:{man_qty}|"
                        db.log_trade(man_ticker, man_ent, man_stop, note_str, "")
                        st.rerun()
            else:
                st.caption("Waiting for valid ticker symbol...")

    def on_note_change(t_id, current_qty):
        new_text = st.session_state[f"n_{t_id}"]
        full_note = f"QTY:{current_qty}|{new_text}"
        db.update_notes(t_id, full_note)

    st.subheader("Interactive Trading Log")
    log_data = db.get_journal_data()
    
    if not log_data.empty:
        sl_alerts = []
        profit_alerts = []
        
        for _, row in log_data.iterrows():
            live_techs = get_technical_data(row['ticker'])
            if live_techs:
                live_p = live_techs['price']
                if live_p < row['atr_sl']:
                    sl_alerts.append(f"**{row['ticker']}** dropped below SL (${row['atr_sl']:.2f}) ➔ Current: **${live_p:.2f}**")
                elif live_p > row['entry']:
                    profit_alerts.append(f"**{row['ticker']}** crossed above Entry (${row['entry']:.2f}) ➔ Current: **${live_p:.2f}**")
                    
        if sl_alerts or profit_alerts:
            for alert in sl_alerts: st.error(f"🚨 {alert}")
            for alert in profit_alerts: st.success(f"📈 {alert}")
            st.write("") 
        
        for _, row in log_data.iterrows():
            st.markdown(f'<div class="journal-row">', unsafe_allow_html=True)
            
            raw_notes = str(row['notes']) if pd.notna(row['notes']) else ""
            qty = 1.0
            display_notes = raw_notes
            
            if raw_notes.startswith("QTY:"):
                parts = raw_notes.split("|", 1)
                try:
                    qty_str = parts[0].replace("QTY:", "").strip()
                    qty = float(qty_str)
                    display_notes = parts[1].strip() if len(parts) > 1 else ""
                except:
                    pass

            risk_pct = ((row['entry'] - row['atr_sl']) / row['entry']) * 100 if row['entry'] > 0 else 0
            
            live_techs = get_technical_data(row['ticker'])
            status_html = ""
            if live_techs:
                live_p = live_techs['price']
                profit_per_share = live_p - row['entry']
                total_profit_dlr = profit_per_share * qty
                profit_pct = (profit_per_share / row['entry']) * 100 if row['entry'] > 0 else 0
                
                if live_p <= row['atr_sl']:
                    status_html = f"<span style='background: rgba(239,68,68,0.15); color: #EF4444; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; margin-left: 8px;'>🚨 SL HIT (${live_p:.2f}) | P&L: {profit_pct:.2f}% (${total_profit_dlr:.2f})</span>"
                elif profit_per_share > 0:
                    status_html = f"<span style='background: rgba(16,185,129,0.15); color: #10B981; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; margin-left: 8px;'>🟢 PROFIT (${live_p:.2f}) | P&L: +{profit_pct:.2f}% (+${total_profit_dlr:.2f})</span>"
                else:
                    status_html = f"<span style='background: rgba(245,158,11,0.15); color: #F59E0B; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 700; margin-left: 8px;'>🟡 ACTIVE (${live_p:.2f}) | P&L: {profit_pct:.2f}% (${total_profit_dlr:.2f})</span>"
            
            html_info = f"""
            <div style='display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; margin-bottom: 12px;'>
                <div style='display: flex; align-items: center; flex-wrap: wrap; gap: 6px;'>
                    <span style='color:#3B82F6; font-size: 1.25rem; font-weight: 800; margin-right: 4px;'>{row['ticker']}</span>
                    {status_html}
                </div>
            </div>
            <div style='display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px;'>
                <div class='data-pill'>Ent: <b>${row['entry']:.2f}</b></div>
                <div class='data-pill'>SL: <b style='color:#EF4444;'>${row['atr_sl']:.2f}</b> <span style='font-size: 0.75rem; color:#EF4444; margin-left:2px;'>(-{risk_pct:.1f}%)</span></div>
                <div class='data-pill'>Qty: <b>{qty}</b></div>
            </div>
            """
            st.markdown(html_info, unsafe_allow_html=True)
            
            try:
                clean_date = pd.to_datetime(row['timestamp']).strftime('%d/%m/%Y %H:%M')
            except:
                clean_date = row['timestamp']
            st.markdown(f"<div style='color: #71717A; font-size: 0.75rem; margin-bottom: 15px;'>📅 Logged on: {clean_date}</div>", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([2.5, 1, 1.5])
            with c1: show_img = st.toggle("🔍 View Chart", key=f"show_{row['id']}")
            with c2: edit_mode = st.toggle("✏️ Edit", key=f"edit_mode_{row['id']}")
            with c3:
                if st.button("🗑️ Delete", key=f"del_{row['id']}", use_container_width=True):
                    db.delete_trade(row['id'])
                    st.rerun()
            
            if edit_mode:
                ec1, ec2, ec3, ec4 = st.columns(4)
                new_ent = ec1.number_input("Edit Entry", value=float(row['entry']), key=f"ed_e_{row['id']}")
                new_qty = ec2.number_input("Edit Qty", value=float(qty), key=f"ed_q_{row['id']}")
                new_sl = ec3.number_input("Edit SL", value=float(row['atr_sl']), key=f"ed_s_{row['id']}")
                
                if ec4.button("💾 Save", key=f"save_{row['id']}", use_container_width=True):
                    update_trade_data_supabase(db, row['id'], new_ent, new_sl)
                    new_full_note = f"QTY:{new_qty}|{display_notes}"
                    db.update_notes(row['id'], new_full_note)
                    st.rerun()
            
            if show_img and row.get('image_data'):
                decoded = base64.b64decode(row['image_data'])
                st.image(decoded, use_container_width=True)
            elif show_img:
                st.info("No chart available.")
            
            if display_notes.startswith("Category:"):
                display_notes = ""
                
            st.text_input("Notes:", value=display_notes, key=f"n_{row['id']}", placeholder="Add notes...", on_change=on_note_change, args=(row['id'], qty))
            st.markdown('</div>', unsafe_allow_html=True)

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

# --- HIGH-END PROFESSIONAL CSS ---
st.markdown("""
<style>
    /* Global Theme & Typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    .stApp { 
        background-color: #090B10; 
        color: #E2E8F0; 
        font-family: 'Inter', sans-serif; 
    }

    /* Hide Streamlit Default UI Elements */
    header[data-testid="stHeader"] { display: none !important; }
    footer { display: none !important; }
    [data-testid="stAppViewBlocker"], div[data-testid="stLoading"] { display: none !important; }

    /* Top Market Pulse Metrics */
    [data-testid="metric-container"] {
        background-color: #121722;
        border: 1px solid #1F2636;
        padding: 15px 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    div[data-testid="stMetricValue"] { font-size: 1.5rem !important; color: #10B981; font-weight: 700; }
    div[data-testid="stMetricLabel"] { font-size: 0.9rem !important; color: #94A3B8; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }

    /* Setup Cards with Hover Effects */
    .setup-card { 
        background-color: #121722; 
        padding: 24px; 
        border-radius: 14px; 
        margin-bottom: 24px; 
        border: 1px solid #1F2636; 
        box-shadow: 0 8px 16px -4px rgba(0, 0, 0, 0.4);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .setup-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 20px -4px rgba(0, 0, 0, 0.6);
        border-color: #2A3441;
    }

    /* Technical Information Box */
    .tech-box { 
        background: linear-gradient(145deg, #171E2D, #0F131D);
        padding: 18px; 
        border-radius: 10px; 
        font-size: 0.95rem; 
        margin: 16px 0; 
        border-left: 4px solid #3B82F6; 
        border-top: 1px solid #1F2636;
        border-right: 1px solid #1F2636;
        border-bottom: 1px solid #1F2636;
        line-height: 1.7;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
    }

    /* Customizing Streamlit Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #121722;
        border-radius: 8px 8px 0 0;
        padding: 0 20px;
        color: #94A3B8;
        border: 1px solid #1F2636;
        border-bottom: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3B82F6 !important;
        color: white !important;
        font-weight: 600;
        border-color: #3B82F6 !important;
    }

    /* Dividers */
    hr { margin: 1.5em 0; border-color: #1F2636; }

    /* Journal Rows */
    .journal-row { 
        background-color: #121722; 
        padding: 18px; 
        border-radius: 10px; 
        margin-bottom: 12px; 
        border: 1px solid #1F2636; 
        transition: background-color 0.2s;
    }
    .journal-row:hover { background-color: #171E2D; }
    .journal-header { color: #64748B; font-size: 0.85rem; margin-bottom: 8px; }

    @media (max-width: 768px) {
        .setup-card { padding: 15px; }
        .tech-box { font-size: 0.85rem; padding: 12px; }
        div[data-testid="stMetricValue"] { font-size: 1.1rem !important; }
        .stTabs [data-baseweb="tab"] { padding: 0 10px; font-size: 0.8rem; }
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
        except:
            pass
    return pulse


@st.cache_data(ttl=300)
def get_technical_data(ticker):
    try:
        df = yf.Ticker(ticker).history(period="3mo")
        if len(df) < 20: return None
        price = df['Close'].iloc[-1]

        df['High-Low'] = df['High'] - df['Low']
        df['High-PrevClose'] = abs(df['High'] - df['Close'].shift(1))
        df['Low-PrevClose'] = abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = df[['High-Low', 'High-PrevClose', 'Low-PrevClose']].max(axis=1)
        atr = df['TR'].rolling(14).mean().iloc[-1]

        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        vol_today = df['Volume'].iloc[-1]
        vol_ratio = (vol_today / vol_avg) if vol_avg > 0 else 1

        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]

        return {"price": price, "ATR": atr, "RSI": rsi, "VolRatio": vol_ratio}
    except:
        return None


@st.cache_data(ttl=86400)
def get_upcoming_earnings():
    major_tickers = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NFLX', 'AMD', 'JPM', 'DIS']
    results = []
    for t in major_tickers:
        try:
            ticker_obj = yf.Ticker(t)
            added = False
            try:
                cal = ticker_obj.calendar
                if isinstance(cal, dict) and 'Earnings Date' in cal:
                    dates = cal['Earnings Date']
                    if not isinstance(dates, list): dates = [dates]
                    future_dates = [pd.to_datetime(d).date() for d in dates if
                                    pd.to_datetime(d).date() >= datetime.now().date()]
                    if future_dates:
                        next_date = min(future_dates)
                        days_left = (next_date - datetime.now().date()).days
                        eps = cal.get('Earnings Average', 'N/A')
                        eps_str = f"${float(eps):.2f}" if eps != 'N/A' and pd.notna(eps) else 'N/A'
                        results.append(
                            {"Ticker": t, "Report Date": next_date.strftime('%Y-%m-%d'), "Days Left": days_left,
                             "Est. EPS": eps_str})
                        added = True
            except:
                pass
            if not added:
                try:
                    ed = ticker_obj.earnings_dates
                    if ed is not None and not ed.empty:
                        future_dates = ed[ed.index.tz_localize(None) >= pd.Timestamp.now().normalize()]
                        if not future_dates.empty:
                            next_date = future_dates.index.min()
                            days_left = (next_date.tz_localize(None) - datetime.now()).days
                            eps = future_dates.loc[next_date, 'EPS Estimate']
                            eps_str = f"${float(eps):.2f}" if pd.notna(eps) else 'N/A'
                            results.append(
                                {"Ticker": t, "Report Date": next_date.strftime('%Y-%m-%d'), "Days Left": days_left,
                                 "Est. EPS": eps_str})
                except:
                    pass
        except Exception:
            pass
    if results:
        df = pd.DataFrame(results)
        df = df.drop_duplicates(subset=['Ticker']).sort_values(by="Days Left")
        return df
    return pd.DataFrame()


# ==========================================
# HEADER & MARKET PULSE
# ==========================================
st.markdown(
    "<h2 style='color: white; margin-bottom: 20px; font-weight: 700; letter-spacing: -0.5px;'>MARKET TERMINAL</h2>",
    unsafe_allow_html=True)

pulse_data = get_market_pulse()
if pulse_data:
    cols = st.columns(len(pulse_data))
    for i, (t, data) in enumerate(pulse_data.items()):
        color = "normal" if data['change'] >= 0 else "inverse"
        if t == "^VIX": color = "inverse" if data['change'] >= 0 else "normal"
        cols[i].metric(data['name'], f"${data['price']:.2f}", f"{data['change']:+.2f}%", delta_color=color)
st.divider()

# ==========================================
# GLOBAL SYNC BUTTON
# ==========================================
if st.button("🔄 Sync All Discord Channels", use_container_width=True, type="primary"):
    with st.spinner("Fetching setups from all channels..."):
        try:
            DiscordListener(os.getenv("DISCORD_TOKEN")).fetch_new_images()
            time.sleep(1.0)
            st.session_state.visible_count_breakouts = 3
            st.session_state.visible_count_trendlines = 3
            st.session_state.visible_count_fibonacci = 3
            st.rerun()
        except Exception as e:
            st.error(f"Sync Error: {e}")

st.divider()


# ==========================================
# REUSABLE TAB BUILDER FUNCTION
# ==========================================
def render_setup_tab(category_name, state_key):
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(f"<h3 style='color: #E2E8F0; font-weight: 600;'>{category_name.capitalize()} Scanner</h3>",
                    unsafe_allow_html=True)
    with col2:
        atr_multiplier = st.number_input("Risk: SL (ATR Multiplier)", min_value=0.5, max_value=5.0, value=1.5, step=0.5,
                                         key=f"atr_{category_name}")

    img_dir = os.path.join("data", f"discord_{category_name}")
    if os.path.exists(img_dir):
        files = sorted([f for f in os.listdir(img_dir) if f.endswith('.png')],
                       key=lambda x: int(x.split('_')[-1].split('.')[0]) if '_' in x else 0, reverse=True)
        seen = set()
        unique_setups = []

        invalid_placeholders = ["SETUP", "IMAGE", "IMG", "UNKNOWN", "EMBED"]

        for f in files:
            ticker = f.split('_')[0].upper()
            if ticker in invalid_placeholders or ticker not in seen:
                if ticker not in invalid_placeholders:
                    seen.add(ticker)
                unique_setups.append((f, ticker))

        for f, original_ticker in unique_setups[:st.session_state[state_key]]:
            full_img_path = os.path.join(img_dir, f)
            st.markdown(f'<div class="setup-card">', unsafe_allow_html=True)
            col_img, col_info = st.columns([1.2, 1])

            with col_img:
                st.image(full_img_path, use_container_width=True)

            with col_info:
                is_invalid = original_ticker in invalid_placeholders
                user_ticker = st.text_input("Ticker Symbol:", value="" if is_invalid else original_ticker,
                                            key=f"tick_{f}_{category_name}")
                user_ticker = user_ticker.upper().strip()

                techs = get_technical_data(user_ticker) if user_ticker else None

                if techs:
                    p = techs['price']
                    st.markdown(
                        f"<h3 style='color: #10B981; margin-top: 0;'>{user_ticker} <span style='color: #64748B; font-size: 0.8em;'>| ${p:.2f}</span></h3>",
                        unsafe_allow_html=True)

                    dynamic_sl = p - (techs['ATR'] * atr_multiplier)

                    # חישוב אחוז סיכון להמלצה
                    risk_percent_suggested = 0
                    if p > 0:
                        risk_percent_suggested = ((p - dynamic_sl) / p) * 100

                    rsi_color = "🔴 High" if techs['RSI'] > 70 else "🟢 Low" if techs['RSI'] < 30 else "⚪ Neutral"
                    vol_color = "🔥 High" if techs['VolRatio'] > 1.5 else "🧊 Low"

                    st.markdown(f"""
                    <div class="tech-box">
                        <b style="color: #94A3B8;">RSI:</b> {techs['RSI']:.0f} ({rsi_color})<br>
                        <b style="color: #94A3B8;">Vol:</b> {techs['VolRatio']:.1f}x ({vol_color})<br>
                        <b style="color: #94A3B8;">ATR:</b> ${techs['ATR']:.2f}<br>
                        <hr style="margin: 8px 0; border-color: #1F2636;">
                        <b style="color: #94A3B8;">Suggested SL:</b> <span style="color: #EF4444; font-weight: 700; font-size: 1.1em;">${dynamic_sl:.2f} (-{risk_percent_suggested:.1f}%)</span>
                    </div>
                    """, unsafe_allow_html=True)

                    col_ent, col_sl = st.columns(2)
                    with col_ent:
                        manual_entry = st.number_input("Entry Target", value=float(p), step=0.1,
                                                       key=f"ent_{f}_{category_name}")
                    with col_sl:
                        manual_sl = st.number_input("Stop Loss", value=float(dynamic_sl), step=0.1,
                                                    key=f"sl_{f}_{category_name}")

                    if st.button("📝 Log Trade", use_container_width=True, type="primary",
                                 key=f"log_{f}_{category_name}"):
                        db.log_trade(user_ticker, manual_entry, manual_sl, f"Category: {category_name.capitalize()}",
                                     full_img_path)
                        st.success("Successfully logged & image saved!")
                else:
                    if is_invalid and not user_ticker:
                        st.warning("⚠️ No ticker identified. Please type the ticker symbol above to load data.")
                    else:
                        st.warning(f"Data unavailable for '{user_ticker}'.")

                    if st.button("📝 Log Image Only", use_container_width=True, key=f"log_empty_{f}_{category_name}"):
                        db.log_trade(user_ticker if user_ticker else "SETUP", 0.0, 0.0,
                                     f"Category: {category_name.capitalize()}", full_img_path)
                        st.success("Logged & Image Saved!")

            st.markdown('</div>', unsafe_allow_html=True)

        if len(unique_setups) > st.session_state[state_key]:
            if st.button("⬇️ Load More Setups", use_container_width=True, key=f"load_{category_name}"):
                st.session_state[state_key] += 3
                st.rerun()


# ==========================================
# MAIN TABS CREATION
# ==========================================
t1, t2, t3, t4, t5 = st.tabs(["🚀 Breakouts", "📈 Trendlines", "📉 Fibonacci", "📅 Earnings", "📓 Manage Log"])

with t1:
    render_setup_tab("breakouts", "visible_count_breakouts")

with t2:
    render_setup_tab("trendlines", "visible_count_trendlines")

with t3:
    render_setup_tab("fibonacci", "visible_count_fibonacci")

with t4:
    st.markdown("<h3 style='color: #E2E8F0;'>Upcoming Earnings (Market Movers)</h3>", unsafe_allow_html=True)
    with st.spinner("Fetching data..."):
        earnings_df = get_upcoming_earnings()
    if not earnings_df.empty:
        def highlight_close_dates(val):
            return 'color: #EF4444; font-weight: bold;' if isinstance(val, int) and val <= 7 else ''


        st.dataframe(earnings_df.style.map(highlight_close_dates, subset=['Days Left']), use_container_width=True,
                     hide_index=True)

with t5:
    journal_df = db.get_journal_data()

    if not journal_df.empty:
        for _, row in journal_df.iterrows():
            st.markdown(f'<div class="journal-row">', unsafe_allow_html=True)

            c_info, c_action = st.columns([3, 1])

            with c_info:
                # חישוב אחוז סיכון בפועל מהיומן
                risk_pct = 0
                if row['entry'] > 0 and row['atr_sl'] > 0:
                    risk_pct = ((row['entry'] - row['atr_sl']) / row['entry']) * 100

                risk_display = f"(-{risk_pct:.1f}%)" if risk_pct > 0 else ""

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
                st.markdown(f"<div class='journal-header'>Logged on: {row['timestamp']}</div>", unsafe_allow_html=True)

                new_notes = st.text_input("Notes:", value=row['notes'], key=f"edit_notes_{row['id']}")
                if new_notes != row['notes']:
                    db.update_notes(row['id'], new_notes)
                    st.rerun()

            with c_action:
                if st.button("🗑️ Delete", key=f"del_{row['id']}", use_container_width=True):
                    db.delete_trade(row['id'])
                    st.rerun()

                has_image = bool(row.get('image_data'))
                if has_image:
                    with st.expander("🖼️ View Chart"):
                        try:
                            decoded_img = base64.b64decode(row['image_data'])
                            st.image(decoded_img, use_container_width=True)
                        except Exception as e:
                            st.error("Failed to load image.")
                else:
                    st.button("🖼️ No Chart", disabled=True, key=f"no_img_{row['id']}", use_container_width=True)

            st.markdown('</div>', unsafe_allow_html=True)

        st.divider()
        csv = journal_df.drop(columns=['image_data', 'id'], errors='ignore').to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Clean CSV", data=csv, file_name='journal.csv', mime='text/csv')
    else:
        st.info("Log is empty.")
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import base64
import warnings
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Notebook Display Support
try:
    from IPython.display import display, HTML
    IN_NOTEBOOK = True
except ImportError:
    IN_NOTEBOOK = False

warnings.filterwarnings('ignore')

class Style:
    GREEN = '\033[92m'
    RED = '\033[91m'
    GOLD = '\033[93m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

# ======================================================
# 🚀 1. CALCULATE NIFTY 500 MBR
# ======================================================
print(f"{Style.GOLD}>>> STEP 1: CALCULATING NIFTY 500 MBR SIGNAL...{Style.RESET}")

try:
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    df_tickers = pd.read_csv(url)
    nifty500_symbols = [s.strip() + ".NS" for s in df_tickers['Symbol'].tolist() if s.strip() != 'DUMMYHDLVR']
except Exception as e:
    print(f"Error: {e}")
    nifty500_symbols = []

mbr_signal_text, mbr_reason_text = "N/A", "Data Error"
current_mbr, prev_mbr, mbr_change = 0.0, 0.0, 0.0
breadth_b64 = ""

if nifty500_symbols:
    mbr_data = yf.download(nifty500_symbols, period="60d", interval="1d", auto_adjust=True, progress=False)['Close']
    mbr_data = mbr_data.dropna(axis=1, how='all')
    daily_returns = mbr_data.pct_change()
    daily_advances = (daily_returns > 0).sum(axis=1)
    daily_declines = (daily_returns < 0).sum(axis=1)
    avg_advances = daily_advances.rolling(window=20).mean()
    avg_declines = daily_declines.rolling(window=20).mean()
    mbr_series = (avg_advances - avg_declines) / (avg_advances + avg_declines)
    mbr_series = mbr_series.dropna()

    if not mbr_series.empty:
        current_mbr = mbr_series.iloc[-1]
        prev_mbr = mbr_series.iloc[-2] if len(mbr_series) > 1 else 0.0
        mbr_change = current_mbr - prev_mbr

        if current_mbr > 0.10:
            mbr_signal_text, sig_color = "STRONG BUY (Bullish Herding)", '#00ff00'
            mbr_reason_text = "Market mein consistent kharidari hai."
        elif current_mbr > 0.0:
            mbr_signal_text, sig_color = "WEAK BUY / NEUTRAL", '#ffff00'
            mbr_reason_text = "Trend positive hai par momentum weak hai."
        elif current_mbr < -0.10:
            mbr_signal_text, sig_color = "STRONG SELL (Bearish Herding)", '#ff0000'
            mbr_reason_text = "Market mein heavy bikwali hai."
        else:
            mbr_signal_text, sig_color = "NEUTRAL / SIDEWAYS", '#cccccc'
            mbr_reason_text = "Market directionless hai."

        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 3.5))
        ax.plot(mbr_series.index, mbr_series.values, color=sig_color, linewidth=2)
        ax.axhline(0, color='gray', linestyle='--')
        ax.axhline(0.10, color='green', linestyle=':')
        ax.axhline(-0.10, color='red', linestyle=':')
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', bbox_inches='tight', facecolor='#1e1e1e')
        breadth_b64 = base64.b64encode(img_buf.getvalue()).decode('utf-8')
        plt.close()

# ======================================================
# 🔍 2. SCANNER LOGIC
# ======================================================
my_tickers = ["TCS.NS", "INFY.NS", "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "MARUTI.NS", "ULTRACEMCO.NS", "ONGC.NS"] # Shortened for example
sector_map = {"TCS": "IT", "INFY": "IT", "HCLTECH": "IT", "SUNPHARMA": "PHARMA", "TITAN": "CONSUMER", "MARUTI": "AUTO", "ULTRACEMCO": "CEMENT", "ONGC": "ENERGY"}

all_tickers = list(set(my_tickers + ["^NSEI"]))
data = yf.download(all_tickers, period="2mo", group_by='ticker', progress=False)
bullish_candidates, all_signals = [], []
nifty = data['^NSEI']['Close']

for t in my_tickers:
    try:
        df = data[t].dropna()
        if len(df) < 25: continue
        curr_p = df['Close'].iloc[-1]
        rs_line = df['Close'] / nifty.reindex(df.index).ffill()
        rs_score = ((rs_line.iloc[-1] - rs_line.iloc[-21]) / rs_line.iloc[-21]) * 100
        df['MFI'] = (df['High'] - df['Low']) / (df['Volume'] + 1) * 100000
        if df['MFI'].iloc[-1] > df['MFI'].iloc[-2] and df['Volume'].iloc[-1] > df['Volume'].iloc[-2]:
            item = {"Symbol": t.replace(".NS",""), "Sector": sector_map.get(t.replace(".NS",""), "Other"), "Price": curr_p, "RS": rs_score, "Signal": "BUY NOW", "SL": curr_p * 0.95}
            bullish_candidates.append(item)
            all_signals.append(item)
    except: continue

# ======================================================
# 🍰 3. GENERATE HTML
# ======================================================
html_rows = ""
for row in all_signals:
    html_rows += f"<tr><td>{row['Symbol']}</td><td>{row['Sector']}</td><td>{row['Price']:.2f}</td><td>{row['RS']:.2f}</td><td style='color:#0f0'>{row['Signal']}</td><td>{row['SL']:.2f}</td></tr>"

html_content = f"""
<html>
<body style="background:#121212; color:#eee; font-family:sans-serif;">
    <div style="background:#1e1e1e; padding:20px; border-radius:8px;">
        <h2 style="color:gold;">MARKET BREADTH: {mbr_signal_text}</h2>
        <p>Current MBR: {current_mbr:.4f} | Change: {mbr_change:+.4f}</p>
        <img src="data:image/png;base64,{breadth_b64}" width="600">
        <hr>
        <h2 style="color:gold;">BULLISH WATCHLIST</h2>
        <table border="1" style="width:100%; border-collapse:collapse; text-align:left;">
            <tr><th>Symbol</th><th>Sector</th><th>Price</th><th>RS</th><th>Signal</th><th>SL</th></tr>
            {html_rows}
        </table>
    </div>
</body>
</html>
"""

# ======================================================
# 📧 4. EMAIL SENDING
# ======================================================
def send_email(content):
    sender = os.environ.get("EMAIL_USER")
    password = os.environ.get("EMAIL_PASS")
    receiver = os.environ.get("EMAIL_RECEIVER")
    
    if not sender or not password:
        print("Credentials missing!")
        return

    msg = MIMEMultipart()
    msg['Subject'] = f"🚀 Market Dashboard - {mbr_signal_text}"
    msg['From'] = sender
    msg['To'] = receiver
    msg.attach(MIMEText(content, 'html'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
            print("✅ Email Sent!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    send_email(html_content)
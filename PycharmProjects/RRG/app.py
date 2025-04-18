import yfinance as yf
import pandas as pd
import plotly.express as px
import streamlit as st

# ========== USER SETTINGS ==========
SMOOTHING_PERIOD = st.number_input('RS Ratio Smoothing Period', min_value=1, max_value=20, value=1)
MOMENTUM_PERIOD = st.number_input('RS Momentum Period', min_value=1, max_value=30, value=14)
TAIL_LENGTH = st.number_input('Tail Length', min_value=1, max_value=20, value=7)
interval = st.selectbox('Select Interval', ['1d', '1wk', '1mo'], index=1)

# Auto-adjust period based on interval
if interval == '1d':
    period = '1y'
elif interval == '1wk':
    period = '5y'
else:
    period = '10y'
st.write(f"🔄 Fetching data for period: **{period}** at interval: **{interval}**")

# NSE Indices
indices = {
    'Nifty Bank': '^NSEBANK',
    'Nifty IT': '^CNXIT',
    'Nifty FMCG': '^CNXFMCG',
    'Nifty Auto': '^CNXAUTO',
    'Nifty Pharma': '^CNXPHARMA',
    'Nifty Metal': '^CNXMETAL',
    'Nifty Realty': '^CNXREALTY',
    'Nifty Energy': '^CNXENERGY',
    'Nifty Financial Services': 'NIFTY_FIN_SERVICE.NS'
}
benchmark = '^NSEI'

# Download data
tickers = list(indices.values()) + [benchmark]
data = yf.download(tickers, period=period, interval=interval)['Close']
data = data.dropna(axis=1)

valid_tickers = data.columns.tolist()
st.write("✅ Valid tickers:", valid_tickers)

# Filter out missing tickers
indices = {name: ticker for name, ticker in indices.items() if ticker in valid_tickers}
if benchmark not in valid_tickers:
    st.warning("⚠️ Benchmark not available. Using fallback ticker.")
    benchmark = valid_tickers[-1] if valid_tickers else None

if not benchmark or not indices:
    st.error("❌ No valid tickers to process.")
    st.stop()

# RS calculations
rs_df = pd.DataFrame()
for name, ticker in indices.items():
    rs_df[name] = data[ticker] / data[benchmark]

for col in rs_df.columns:
    rs_df[col + '_ratio'] = rs_df[col].rolling(window=SMOOTHING_PERIOD).mean() * 100
    rs_df[col + '_momentum'] = rs_df[col].pct_change(periods=MOMENTUM_PERIOD)

# Tail data
tail_data = []
for col in indices.keys():
    ratio_series = rs_df[col + '_ratio'].dropna()
    momentum_series = rs_df[col + '_momentum'].dropna()
    if len(ratio_series) >= TAIL_LENGTH and len(momentum_series) >= TAIL_LENGTH:
        tail_data.append({
            'Name': col,
            'RS Ratio': ratio_series.iloc[-TAIL_LENGTH:],
            'RS Momentum': momentum_series.iloc[-TAIL_LENGTH:],
            'Week': list(range(1, TAIL_LENGTH + 1))
        })

if not tail_data:
    st.warning("⚠️ No tail data found. Try changing your settings.")
    st.stop()

tail_df = pd.DataFrame(tail_data)
tail_df = tail_df.explode(['RS Ratio', 'RS Momentum', 'Week']).reset_index(drop=True)

# Plot chart
fig = px.scatter(
    tail_df,
    x='RS Ratio',
    y='RS Momentum',
    color='Name',
    title=f'RRG Chart (Sector Indices vs Nifty 50) — {interval.upper()}',
    width=800,
    height=600
)
fig.update_traces(marker=dict(size=0))  # Hide dots

# Add lines and arrows
for name in indices.keys():
    sector_data = tail_df[tail_df['Name'] == name]
    fig.add_trace(
        px.line(sector_data, x='RS Ratio', y='RS Momentum').data[0]
    )
    if len(sector_data) >= 2:
        latest = sector_data.iloc[-1]
        previous = sector_data.iloc[-2]
        fig.add_annotation(
            x=latest['RS Ratio'], y=latest['RS Momentum'],
            ax=previous['RS Ratio'], ay=previous['RS Momentum'],
            xref='x', yref='y', axref='x', ayref='y',
            showarrow=True, arrowhead=2, arrowsize=1.5,
            arrowwidth=2, arrowcolor='white'
        )

# Quadrants
x_mean = tail_df['RS Ratio'].mean()
y_mean = tail_df['RS Momentum'].mean()
fig.add_shape(type="line", x0=x_mean, y0=tail_df['RS Momentum'].min(),
              x1=x_mean, y1=tail_df['RS Momentum'].max(),
              line=dict(color="white", dash="dash"))
fig.add_shape(type="line", x0=tail_df['RS Ratio'].min(), y0=y_mean,
              x1=tail_df['RS Ratio'].max(), y1=y_mean,
              line=dict(color="white", dash="dash"))

st.plotly_chart(fig)




import yfinance as yf
import pandas as pd
import plotly.express as px
import streamlit as st

# ========== UI SETTINGS ==========
SMOOTHING_PERIOD = st.number_input('RS Ratio Smoothing Period', 1, 20, 1)
MOMENTUM_PERIOD = st.number_input('RS Momentum Period', 1, 30, 14)
TAIL_LENGTH = st.number_input('Tail Length', 1, 20, 7)
interval = st.selectbox('Select Interval', ['1d', '1wk', '1mo'], index=1)

# Choose download period based on interval
period = {'1d': '1y', '1wk': '5y', '1mo': '10y'}[interval]
st.write(f"Fetching data for: `{period}` at `{interval}` interval...")

# ========== SYMBOLS ==========
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

# ========== FETCH DATA ==========
tickers = list(indices.values()) + [benchmark]
df = yf.download(tickers, period=period, interval=interval)['Close']
df = df.dropna(axis=1)
valid_tickers = df.columns.tolist()

# Filter valid indices
indices = {name: ticker for name, ticker in indices.items() if ticker in valid_tickers}
if benchmark not in valid_tickers:
    st.error("Benchmark data not available. Try again later.")
    st.stop()

# ========== CALCULATE RS ==========
rs_df = pd.DataFrame()
for name, ticker in indices.items():
    rs = df[ticker] / df[benchmark]
    rs_df[name + '_ratio'] = rs.rolling(SMOOTHING_PERIOD).mean() * 100
    rs_df[name + '_momentum'] = rs.pct_change(MOMENTUM_PERIOD)

# ========== BUILD TAIL DATA ==========
tail_data = []
for name in indices:
    ratio = rs_df[name + '_ratio'].dropna()
    momentum = rs_df[name + '_momentum'].dropna()
    if len(ratio) >= TAIL_LENGTH and len(momentum) >= TAIL_LENGTH:
        tail_data.append(pd.DataFrame({
            'Name': name,
            'RS Ratio': ratio.iloc[-TAIL_LENGTH:].values,
            'RS Momentum': momentum.iloc[-TAIL_LENGTH:].values,
            'Week': list(range(TAIL_LENGTH))
        }))

if not tail_data:
    st.warning("⚠️ Not enough data. Try reducing the Tail Length or check the internet.")
    st.stop()

tail_df = pd.concat(tail_data)

# ========== PLOT ==========
fig = px.scatter(tail_df, x='RS Ratio', y='RS Momentum', color='Name')
fig.update_traces(marker=dict(size=0))  # Remove dots

# Add lines and arrows
for name in tail_df['Name'].unique():
    data = tail_df[tail_df['Name'] == name]
    fig.add_trace(px.line(data, x='RS Ratio', y='RS Momentum').data[0])
    if len(data) >= 2:
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        fig.add_annotation(
            x=latest['RS Ratio'], y=latest['RS Momentum'],
            ax=prev['RS Ratio'], ay=prev['RS Momentum'],
            xref='x', yref='y', axref='x', ayref='y',
            showarrow=True, arrowhead=2, arrowsize=1.5,
            arrowwidth=2, arrowcolor='white'
        )

# Draw quadrant lines
x_mean = tail_df['RS Ratio'].mean()
y_mean = tail_df['RS Momentum'].mean()
fig.add_shape(type='line', x0=x_mean, y0=tail_df['RS Momentum'].min(),
              x1=x_mean, y1=tail_df['RS Momentum'].max(),
              line=dict(color='white', dash='dash'))
fig.add_shape(type='line', x0=tail_df['RS Ratio'].min(), y0=y_mean,
              x1=tail_df['RS Ratio'].max(), y1=y_mean,
              line=dict(color='white', dash='dash'))

st.plotly_chart(fig)





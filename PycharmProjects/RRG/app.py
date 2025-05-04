import yfinance as yf
import pandas as pd
import plotly.express as px

# ========== USER SETTINGS ==========
# You can change these:
SMOOTHING_PERIOD = 1  # For RS Ratio smoothing
MOMENTUM_PERIOD = 14    # For RS Momentum calculation
TAIL_LENGTH = 7        # How many periods of tail to show
TIMEFRAME = 'weekly'   # Options: 'weekly' or 'monthly'

# Use actual NSE sector indices (not stocks) and Nifty Financial Services
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
benchmark = '^NSEI'  # Nifty 50 (benchmark)

# Determine interval and period based on timeframe
if TIMEFRAME == 'weekly':
    interval = '1wk'
    period = '6mo'
elif TIMEFRAME == 'monthly':
    interval = '1mo'
    period = '2y'
else:
    raise ValueError("TIMEFRAME must be 'weekly' or 'monthly'")

# Download data
tickers = list(indices.values()) + [benchmark]
data = yf.download(tickers, period=period, interval=interval)['Close']
data = data.dropna(axis=1)

# Filter indices and benchmark to only valid ones
valid_tickers = data.columns.tolist()
indices = {name: ticker for name, ticker in indices.items() if ticker in valid_tickers}
if benchmark not in valid_tickers:
    benchmark = valid_tickers[-1]

print("\n✅ Using these sector indices:", list(indices.keys()))
print(f"✅ Using benchmark: {benchmark}")

# Relative Strength calculations
rs_df = pd.DataFrame()
for name, ticker in indices.items():
    rs_df[name] = data[ticker] / data[benchmark]

# RS Ratio and Momentum (smoothed and percent change)
for col in rs_df.columns:
    rs_df[col + '_ratio'] = rs_df[col].rolling(window=SMOOTHING_PERIOD).mean() * 100
    rs_df[col + '_momentum'] = rs_df[col].pct_change(periods=MOMENTUM_PERIOD)

# Get latest TAIL_LENGTH weeks of RS data for tails
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

# Convert to DataFrame
tail_df = pd.DataFrame(tail_data)
tail_df = tail_df.explode(['RS Ratio', 'RS Momentum', 'Week']).reset_index(drop=True)

# Plot the RRG chart with tails (connected by lines)
if not tail_df.empty:
    fig = px.scatter(
        tail_df,
        x='RS Ratio',
        y='RS Momentum',
        text='Name',
        color='Name',
        title=f'RRG Chart (Sector Indices vs Nifty 50) — {TIMEFRAME.title()}',
        width=800,
        height=600
    )

    for name in indices.keys():
        sector_data = tail_df[tail_df['Name'] == name]
        fig.add_trace(
            px.line(sector_data, x='RS Ratio', y='RS Momentum').data[0]
        )

    # Label only the last dot
    fig.update_traces(textposition='top center', showlegend=False)
    for trace in fig.data:
        if trace.text is not None:
            trace.text = [name if i == len(trace.text) - 1 else "" for i, name in enumerate(trace.text)]

    # Quadrant lines
    x_mean = tail_df['RS Ratio'].mean()
    y_mean = tail_df['RS Momentum'].mean()
    fig.add_shape(type="line", x0=x_mean, y0=tail_df['RS Momentum'].min(),
                  x1=x_mean, y1=tail_df['RS Momentum'].max(),
                  line=dict(color="Black", dash="dash"))
    fig.add_shape(type="line", x0=tail_df['RS Ratio'].min(), y0=y_mean,
                  x1=tail_df['RS Ratio'].max(), y1=y_mean,
                  line=dict(color="Black", dash="dash"))

    fig.show()
else:
    print("⚠️ Not enough data to plot RRG chart with tails.")




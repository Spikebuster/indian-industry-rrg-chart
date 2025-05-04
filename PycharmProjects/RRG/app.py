import yfinance as yf
import pandas as pd
import plotly.express as px

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
    'Nifty Financial Services': 'NIFTY_FIN_SERVICE.NS'  # Updated to the correct symbol
}
benchmark = '^NSEI'  # Nifty 50 (benchmark)

# Download 6 months of weekly data
tickers = list(indices.values()) + [benchmark]
data = yf.download(tickers, period='6mo', interval='1wk')['Close']
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

# RS Ratio and Momentum (14-period smoothing and change)
rrg_data = pd.DataFrame()
for col in rs_df.columns:
    rs_df[col + '_ratio'] = rs_df[col].rolling(window=14).mean()
    rs_df[col + '_momentum'] = rs_df[col].pct_change(periods=14)

# Get latest 7-week RS data for tails
tail_data = []
for col in indices.keys():
    ratio_series = rs_df[col + '_ratio'].dropna()
    momentum_series = rs_df[col + '_momentum'].dropna()
    if len(ratio_series) >= 7 and len(momentum_series) >= 7:
        tail_data.append({
            'Name': col,
            'RS Ratio': ratio_series.iloc[-7:],  # Last 7 weeks
            'RS Momentum': momentum_series.iloc[-7:],  # Last 7 weeks
            'Week': list(range(1, 8))  # Labels for each dot
        })

# Convert to DataFrame
tail_df = pd.DataFrame(tail_data)
tail_df = tail_df.explode(['RS Ratio', 'RS Momentum', 'Week']).reset_index(drop=True)

print("\n📊 Tail Data:\n")
print(tail_df)

# Plot the RRG chart with tails (7 dots) connected by lines
if not tail_df.empty:
    # Create a scatter plot for each sector, but with the name only on the last dot
    fig = px.scatter(
        tail_df,
        x='RS Ratio',
        y='RS Momentum',
        text='Name',
        color='Name',
        title='RRG Chart (Sector Indices vs Nifty 50)',
        width=800,
        height=600
    )

    # Add lines connecting the dots (for each sector)
    for name in indices.keys():
        sector_data = tail_df[tail_df['Name'] == name]
        fig.add_trace(
            px.line(sector_data, x='RS Ratio', y='RS Momentum').data[0]
        )

    # Only show the name on the last dot (latest point in the series)
    fig.update_traces(textposition='top center', showlegend=False)

    # Update: remove names from intermediate dots
    for trace in fig.data:
        if trace.text is not None:
            trace.text = [name if i == len(trace.text) - 1 else "" for i, name in enumerate(trace.text)]

    # Add quadrant lines
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





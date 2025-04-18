import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ========== USER SETTINGS ========== 
# Instead of sliders, use text input to allow users to type values
SMOOTHING_PERIOD = st.text_input('RS Ratio Smoothing Period', '1')  # Default to 1
MOMENTUM_PERIOD = st.text_input('RS Momentum Period', '14')    # Default to 14
TAIL_LENGTH = st.text_input('Tail Length', '7')        # Default to 7

# Frequency of the data
data_frequency = st.selectbox('Data Frequency', ['Daily', 'Weekly', 'Monthly'], index=0)

# Convert the user inputs to integers
try:
    SMOOTHING_PERIOD = int(SMOOTHING_PERIOD)
    MOMENTUM_PERIOD = int(MOMENTUM_PERIOD)
    TAIL_LENGTH = int(TAIL_LENGTH)
except ValueError:
    st.error("Please enter valid integers for the input fields.")
    st.stop()

# Set interval based on user selection
if data_frequency == 'Daily':
    interval = '1d'
elif data_frequency == 'Weekly':
    interval = '1wk'
else:  # Monthly
    interval = '1mo'

# ========== SECTOR INDICES AND BENCHMARK ========== 
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

# Set the maximum period (this can be adjusted)
period = 'max'

# Download data
tickers = list(indices.values()) + [benchmark]
data = yf.download(tickers, period=period, interval=interval)['Close']
data = data.dropna(axis=1)

# Filter indices and benchmark to only valid ones
valid_tickers = data.columns.tolist()
indices = {name: ticker for name, ticker in indices.items() if ticker in valid_tickers}
if benchmark not in valid_tickers:
    if valid_tickers:
        benchmark = valid_tickers[-1]
    else:
        st.error("⚠️ No valid data found for the selected timeframe.")
        st.stop()

# ========== RELATIVE STRENGTH CALCULATIONS ========== 
rs_df = pd.DataFrame()
for name, ticker in indices.items():
    rs_df[name] = data[ticker] / data[benchmark]

# RS Ratio and Momentum (smoothed and percent change)
for col in rs_df.columns:
    rs_df[col + '_ratio'] = rs_df[col].rolling(window=SMOOTHING_PERIOD).mean() * 100
    rs_df[col + '_momentum'] = rs_df[col].pct_change(periods=MOMENTUM_PERIOD)

# ========== TAIL DATA FOR RRG CHART ========== 
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
            'Period': list(range(1, TAIL_LENGTH + 1))
        })

# Convert to DataFrame
if tail_data:
    tail_df = pd.DataFrame(tail_data)
    tail_df = tail_df.explode(['RS Ratio', 'RS Momentum', 'Period']).reset_index(drop=True)

    # Plot the RRG chart with tails (connected by lines)
    fig = px.scatter(
        tail_df,
        x='RS Ratio',
        y='RS Momentum',
        color='Name',
        title=f'RRG Chart (Sector Indices vs Nifty 50) — {data_frequency}',
        width=800,
        height=600
    )

    # Remove dots for all data points
    fig.update_traces(marker=dict(size=0))  # This will hide the dots

    # Add lines (tails) connecting the previous and current points
    for name in indices.keys():
        sector_data = tail_df[tail_df['Name'] == name]
        fig.add_trace(
            px.line(sector_data, x='RS Ratio', y='RS Momentum').data[0]
        )

        # Add arrow instead of dot at latest point
        latest_point = sector_data.iloc[-1]
        previous_point = sector_data.iloc[-2]
        fig.add_annotation(
            x=latest_point['RS Ratio'],
            y=latest_point['RS Momentum'],
            ax=previous_point['RS Ratio'],
            ay=previous_point['RS Momentum'],
            xref='x', yref='y', axref='x', ayref='y',
            showarrow=True,
            arrowhead=2,
            arrowsize=1.5,
            arrowwidth=2,
            arrowcolor='white'
        )

    # Quadrant lines
    x_mean = tail_df['RS Ratio'].mean()
    y_mean = tail_df['RS Momentum'].mean()
    fig.add_shape(type="line", x0=x_mean, y0=tail_df['RS Momentum'].min(),
                  x1=x_mean, y1=tail_df['RS Momentum'].max(),
                  line=dict(color="white", dash="dash"))
    fig.add_shape(type="line", x0=tail_df['RS Ratio'].min(), y0=y_mean,
                  x1=tail_df['RS Ratio'].max(), y1=y_mean,
                  line=dict(color="white", dash="dash"))

    # Show plot inline with Streamlit
    st.plotly_chart(fig)
else:
    st.warning("⚠️ Not enough data to plot RRG chart. Try lowering the tail or smoothing periods.")

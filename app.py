import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="UW Swing Trade & GEX Scanner", layout="wide")

st.title("🐋 Swing Trade Scanner with GEX Analysis")

# Sidebar Configuration
st.sidebar.header("API Configuration")
api_key = st.sidebar.text_input("Unusual Whales API Key", type="password")
min_dte = st.sidebar.slider("Minimum Days to Expiration (DTE)", 14, 180, 30)
min_premium = st.sidebar.number_input("Minimum Trade Premium ($)", value=100000, step=25000)

headers = {
    "Authorization": f"Bearer {api_key}",
    "Accept": "application/json"
} if api_key else {}

BASE_URL = "https://api.unusualwhales.com/api"

def fetch_flow_alerts():
    url = f"{BASE_URL}/option-trades/flow-alerts"
    params = {"min_premium": min_premium}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return pd.DataFrame(response.json().get("data", []))
    return pd.DataFrame()

def fetch_gex(ticker):
    url = f"{BASE_URL}/stock/{ticker}/greek-exposure"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("data", {})
    return {}

if st.sidebar.button("Run Swing Scanner"):
    if not api_key:
        st.error("Please enter your Unusual Whales API Key in the sidebar.")
    else:
        with st.spinner("Fetching institutional flow and calculating GEX..."):
            df_flow = fetch_flow_alerts()
            
        if not df_flow.empty:
            # Filter for swing criteria (DTE >= min_dte and ASK fills)
            swing_df = df_flow[
                (df_flow["dte"] >= min_dte) & 
                (df_flow["side"] == "ASK")
            ].copy()
            
            st.write(f"### High-Conviction Flow Alerts (DTE ≥ {min_dte})")
            st.dataframe(
                swing_df[["ticker", "strike", "option_type", "expiration", "dte", "premium", "sentiment"]], 
                use_container_width=True
            )
            
            # GEX Analysis for Top Tickers
            top_tickers = swing_df["ticker"].unique()[:4] if "ticker" in swing_df.columns else []
            
            if len(top_tickers) > 0:
                st.write("### Gamma Exposure (GEX) Volatility Check")
                cols = st.columns(len(top_tickers))
                
                for idx, ticker in enumerate(top_tickers):
                    gex_data = fetch_gex(ticker)
                    if gex_data:
                        call_gamma = float(gex_data.get("call_gamma", 0))
                        put_gamma = float(gex_data.get("put_gamma", 0))
                        net_gex = call_gamma + put_gamma  # Put gamma is negative in UW API
                        
                        env = "🚀 Trend Potential (Short Gamma)" if net_gex < 0 else "⏸️ Suppressed Volatility (Long Gamma)"
                        
                        with cols[idx]:
                            st.metric(label=f"{ticker} Net GEX", value=f"${net_gex:,.0f}")
                            st.caption(f"**State:** {env}")
        else:
            st.info("No flow alerts matched your criteria.")

import streamlit as st
import pandas as pd
import requests

st.set_page_config(
    page_title="Creative Intelligence Dashboard",
    layout="wide"
)

ACCESS_TOKEN = st.secrets["META_ACCESS_TOKEN"]
AD_ACCOUNT_ID = st.secrets["AD_ACCOUNT_ID"]

def get_insights():
    url = f"https://graph.facebook.com/v25.0/act_{AD_ACCOUNT_ID}/insights"
    params = {
        "level": "ad",
        "fields": "ad_id,ad_name,spend,impressions,reach,frequency,cpm,cpc,ctr,actions,cost_per_action_type",
        "limit": 50,
        "access_token": ACCESS_TOKEN
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "error" in data:
        st.error(data["error"]["message"])
        return pd.DataFrame()

    rows = []
    for item in data.get("data", []):
        leads = 0

        for action in item.get("actions", []):
            if "lead" in action.get("action_type", ""):
                leads += int(action.get("value", 0))

        rows.append({
            "Ad ID": item.get("ad_id"),
            "Ad Name": item.get("ad_name"),
            "Spend": float(item.get("spend", 0)),
            "Impressions": int(item.get("impressions", 0)),
            "Reach": int(item.get("reach", 0)),
            "Frequency": float(item.get("frequency", 0)),
            "CPM": float(item.get("cpm", 0)),
            "CPC": float(item.get("cpc", 0)),
            "CTR": float(item.get("ctr", 0)),
            "Leads": leads,
        })

    return pd.DataFrame(rows)

st.title("🚀 Creative Intelligence Dashboard")
st.success("Meta API Connected Successfully")

df = get_insights()

if df.empty:
    st.warning("No data returned from Meta API.")
else:
    total_spend = df["Spend"].sum()
    total_leads = df["Leads"].sum()
    avg_ctr = df["CTR"].mean()
    avg_cpc = df["CPC"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Spend", f"{total_spend:,.2f} EGP")
    col2.metric("Leads", f"{total_leads:,}")
    col3.metric("Avg CTR", f"{avg_ctr:.2f}%")
    col4.metric("Avg CPC", f"{avg_cpc:.2f} EGP")

    st.subheader("Ad Performance")
    st.dataframe(df, use_container_width=True)

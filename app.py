import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

st.set_page_config(
    page_title="Creative Intelligence Dashboard",
    layout="wide"
)

ACCESS_TOKEN = st.secrets["META_ACCESS_TOKEN"]
AD_ACCOUNT_ID = st.secrets["AD_ACCOUNT_ID"]

def extract_leads(actions):
    leads = 0
    for action in actions or []:
        action_type = action.get("action_type", "")
        if "lead" in action_type:
            leads += int(action.get("value", 0))
    return leads

def get_insights(start_date, end_date):
    url = f"https://graph.facebook.com/v25.0/act_{AD_ACCOUNT_ID}/insights"
    params = {
        "level": "ad",
        "fields": "ad_id,ad_name,spend,impressions,reach,frequency,cpm,cpc,ctr,actions",
        "time_range": f'{{"since":"{start_date}","until":"{end_date}"}}',
        "limit": 100,
        "access_token": ACCESS_TOKEN
    }

    response = requests.get(url, params=params)
    data = response.json()

    if "error" in data:
        st.error(data["error"]["message"])
        return pd.DataFrame()

    rows = []
    for item in data.get("data", []):
        spend = float(item.get("spend", 0))
        leads = extract_leads(item.get("actions", []))
        cpl = spend / leads if leads > 0 else 0

        if leads >= 100 and cpl <= 20:
            status = "🟢 Winner"
        elif leads >= 30 and cpl <= 40:
            status = "🟡 Monitor"
        else:
            status = "🔴 Kill / Weak"

        rows.append({
            "Ad ID": item.get("ad_id"),
            "Ad Name": item.get("ad_name"),
            "Spend": spend,
            "Leads": leads,
            "CPL": cpl,
            "CTR": float(item.get("ctr", 0)),
            "CPC": float(item.get("cpc", 0)),
            "CPM": float(item.get("cpm", 0)),
            "Reach": int(item.get("reach", 0)),
            "Impressions": int(item.get("impressions", 0)),
            "Frequency": float(item.get("frequency", 0)),
            "Status": status
        })

    return pd.DataFrame(rows)

st.title("🚀 Creative Intelligence Dashboard")
st.caption("Meta Ads Creative Performance Intelligence")

with st.sidebar:
    st.header("Filters")
    today = date.today()
    default_start = today - timedelta(days=30)

    start_date = st.date_input("Start Date", default_start)
    end_date = st.date_input("End Date", today)

    st.info("Rules: Winner = Leads ≥ 100 and CPL ≤ 20 EGP")

df = get_insights(start_date, end_date)

if df.empty:
    st.warning("No data returned from Meta API.")
else:
    total_spend = df["Spend"].sum()
    total_leads = df["Leads"].sum()
    avg_cpl = total_spend / total_leads if total_leads > 0 else 0
    avg_ctr = df["CTR"].mean()
    avg_cpc = df["CPC"].mean()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Spend", f"{total_spend:,.2f} EGP")
    col2.metric("Leads", f"{total_leads:,}")
    col3.metric("Avg CPL", f"{avg_cpl:.2f} EGP")
    col4.metric("Avg CTR", f"{avg_ctr:.2f}%")
    col5.metric("Avg CPC", f"{avg_cpc:.2f} EGP")

    st.subheader("🏆 Winners")
    winners = df[df["Status"] == "🟢 Winner"].sort_values("CPL")
    st.dataframe(winners, use_container_width=True)

    st.subheader("📊 All Ads Performance")
    df = df.sort_values(["Status", "CPL"], ascending=[True, True])
    st.dataframe(df, use_container_width=True)

    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="creative_intelligence_dashboard.csv",
        mime="text/csv"
    )

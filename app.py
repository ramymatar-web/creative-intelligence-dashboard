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


def safe_float(value):
    try:
        return float(value)
    except:
        return 0.0


def safe_int(value):
    try:
        return int(value)
    except:
        return 0


def extract_leads(actions):
    leads = 0
    for action in actions or []:
        action_type = action.get("action_type", "")
        if "lead" in action_type:
            leads += safe_int(action.get("value", 0))
    return leads


def calculate_score(row):
    cpl = row.get("CPL", 0)
    leads = row.get("Leads", 0)
    ctr = row.get("CTR", 0)
    cpc = row.get("CPC", 0)
    frequency = row.get("Frequency", 0)

    score = 0

    # CPL score - 40 points
    if cpl > 0 and cpl <= 5:
        score += 40
    elif cpl <= 10:
        score += 32
    elif cpl <= 20:
        score += 24
    elif cpl <= 40:
        score += 12

    # Leads volume score - 25 points
    if leads >= 1000:
        score += 25
    elif leads >= 500:
        score += 20
    elif leads >= 100:
        score += 15
    elif leads >= 30:
        score += 8

    # CTR score - 20 points
    if ctr >= 4:
        score += 20
    elif ctr >= 3:
        score += 15
    elif ctr >= 2:
        score += 10
    elif ctr >= 1:
        score += 5

    # CPC score - 10 points
    if cpc > 0 and cpc <= 2:
        score += 10
    elif cpc <= 4:
        score += 7
    elif cpc <= 7:
        score += 4

    # Frequency score - 5 points
    if frequency > 0 and frequency <= 2.5:
        score += 5
    elif frequency <= 4:
        score += 3

    return min(score, 100)


def classify_status(score):
    if score >= 80:
        return "🟢 Winner"
    elif score >= 60:
        return "🟡 Monitor"
    else:
        return "🔴 Weak"


def detect_creative_type(row):
    video_id = str(row.get("Video ID", "") or "")
    image_url = str(row.get("Image URL", "") or "")
    thumbnail_url = str(row.get("Thumbnail URL", "") or "")

    if video_id and video_id.lower() != "nan":
        return "🎥 Video"
    elif image_url and image_url.lower() != "nan":
        return "🖼️ Image"
    elif thumbnail_url and thumbnail_url.lower() != "nan":
        return "🖼️ Thumbnail"
    else:
        return "❓ Unknown"


def get_performance(start_date, end_date):
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
        spend = safe_float(item.get("spend", 0))
        leads = extract_leads(item.get("actions", []))
        cpl = spend / leads if leads > 0 else 0

        rows.append({
            "Ad ID": item.get("ad_id"),
            "Ad Name": item.get("ad_name"),
            "Spend": spend,
            "Leads": leads,
            "CPL": cpl,
            "CTR": safe_float(item.get("ctr", 0)),
            "CPC": safe_float(item.get("cpc", 0)),
            "CPM": safe_float(item.get("cpm", 0)),
            "Reach": safe_int(item.get("reach", 0)),
            "Impressions": safe_int(item.get("impressions", 0)),
            "Frequency": safe_float(item.get("frequency", 0))
        })

    return pd.DataFrame(rows)


def get_creatives():
    url = f"https://graph.facebook.com/v25.0/act_{AD_ACCOUNT_ID}/ads"
    params = {
        "fields": "id,name,creative{id,name,thumbnail_url,image_url,video_id,object_story_spec}",
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
        creative = item.get("creative", {}) or {}

        rows.append({
            "Ad ID": item.get("id"),
            "Creative ID": creative.get("id", ""),
            "Creative Name": creative.get("name", ""),
            "Thumbnail URL": creative.get("thumbnail_url", ""),
            "Image URL": creative.get("image_url", ""),
            "Video ID": creative.get("video_id", "")
        })

    return pd.DataFrame(rows)


def show_preview(url):
    if not url or pd.isna(url):
        st.markdown(
            """
            <div style="
                height:180px;
                background:#f3f4f6;
                border-radius:12px;
                display:flex;
                align-items:center;
                justify-content:center;
                color:#6b7280;
                font-size:14px;">
                No Preview
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    try:
        st.image(url, use_container_width=True)
    except Exception:
        st.markdown(
            """
            <div style="
                height:180px;
                background:#fff3cd;
                border-radius:12px;
                display:flex;
                align-items:center;
                justify-content:center;
                color:#856404;
                font-size:14px;">
                Preview Not Supported
            </div>
            """,
            unsafe_allow_html=True
        )
        st.link_button("Open Preview", url)


def render_creative_card(row):
    preview_url = row.get("Thumbnail URL") or row.get("Image URL")

    with st.container(border=True):
        show_preview(preview_url)

        st.markdown(f"### {row.get('Ad Name', 'Unnamed Ad')}")
        st.caption(row.get("Creative Name", ""))

        st.write(f"**Creative Type:** {row.get('Creative Type', 'Unknown')}")
        st.write(f"**Winner Score:** {row.get('Winner Score', 0)}/100")
        st.write(f"**Status:** {row.get('Status', '')}")

        c1, c2 = st.columns(2)
        c1.metric("Leads", f"{safe_int(row.get('Leads', 0)):,}")
        c2.metric("CPL", f"{safe_float(row.get('CPL', 0)):.2f} EGP")

        c3, c4 = st.columns(2)
        c3.metric("CTR", f"{safe_float(row.get('CTR', 0)):.2f}%")
        c4.metric("CPC", f"{safe_float(row.get('CPC', 0)):.2f} EGP")

        st.write(f"**Spend:** {safe_float(row.get('Spend', 0)):,.2f} EGP")

        if preview_url:
            st.link_button("Open Creative Preview", preview_url)


st.title("🚀 Creative Intelligence Dashboard")
st.caption("Meta Ads Creative Performance Intelligence")

with st.sidebar:
    st.header("Filters")

    today = date.today()
    default_start = today - timedelta(days=30)

    start_date = st.date_input("Start Date", default_start)
    end_date = st.date_input("End Date", today)

    max_winners = st.slider(
        "Number of Winner Creatives",
        min_value=5,
        max_value=100,
        value=30,
        step=5
    )

    min_score = st.slider(
        "Minimum Winner Score",
        min_value=0,
        max_value=100,
        value=80,
        step=5
    )

    st.info(
        "Winner Score = CPL + Leads Volume + CTR + CPC + Frequency"
    )

performance_df = get_performance(start_date, end_date)
creative_df = get_creatives()

if performance_df.empty:
    st.warning("No performance data returned from Meta API.")
else:
    df = performance_df.merge(creative_df, on="Ad ID", how="left")

    df["Winner Score"] = df.apply(calculate_score, axis=1)
    df["Status"] = df["Winner Score"].apply(classify_status)
    df["Creative Type"] = df.apply(detect_creative_type, axis=1)

    total_spend = df["Spend"].sum()
    total_leads = df["Leads"].sum()
    avg_cpl = total_spend / total_leads if total_leads > 0 else 0
    avg_ctr = df["CTR"].mean()
    avg_cpc = df["CPC"].mean()

    winners = df[df["Winner Score"] >= min_score].sort_values(
        ["Winner Score", "CPL"],
        ascending=[False, True]
    )

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Spend", f"{total_spend:,.2f} EGP")
    col2.metric("Leads", f"{total_leads:,}")
    col3.metric("Avg CPL", f"{avg_cpl:.2f} EGP")
    col4.metric("Avg CTR", f"{avg_ctr:.2f}%")
    col5.metric("Avg CPC", f"{avg_cpc:.2f} EGP")
    col6.metric("Winners", f"{len(winners):,}")

    st.subheader("🏆 Winner Creative Cards")

    if winners.empty:
        st.warning("No winner creatives match the selected score.")
    else:
        selected_winners = winners.head(max_winners)

        rows = [
            selected_winners.iloc[i:i + 3]
            for i in range(0, len(selected_winners), 3)
        ]

        for row_group in rows:
            cols = st.columns(3)
            for col, (_, row) in zip(cols, row_group.iterrows()):
                with col:
                    render_creative_card(row)

    st.subheader("📊 All Ads Performance")

    display_cols = [
        "Ad ID",
        "Ad Name",
        "Creative Type",
        "Creative Name",
        "Creative ID",
        "Video ID",
        "Spend",
        "Leads",
        "CPL",
        "CTR",
        "CPC",
        "CPM",
        "Reach",
        "Impressions",
        "Frequency",
        "Winner Score",
        "Status"
    ]

    final_df = df[display_cols].sort_values(
        ["Winner Score", "CPL"],
        ascending=[False, True]
    )

    st.dataframe(final_df, use_container_width=True)

    st.download_button(
        label="Download CSV",
        data=final_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="creative_intelligence_dashboard.csv",
        mime="text/csv"
    )

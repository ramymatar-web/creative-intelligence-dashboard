import streamlit as st
import pandas as pd
import requests
from datetime import date, timedelta

st.set_page_config(page_title="Creative Intelligence Dashboard", layout="wide")

ACCESS_TOKEN = st.secrets["META_ACCESS_TOKEN"]
AD_ACCOUNT_ID = st.secrets["AD_ACCOUNT_ID"]

st.markdown("""
<style>
.block-container {padding-top: 1.5rem;}
.metric-card {
    background:#fff;border:1px solid #e5e7eb;border-radius:18px;
    padding:16px;box-shadow:0 4px 14px rgba(0,0,0,.04);
}
.creative-card {
    background:#fff;border:1px solid #e5e7eb;border-radius:16px;
    padding:12px;margin-bottom:12px;box-shadow:0 4px 14px rgba(0,0,0,.04);
}
.preview-box img {
    border-radius:12px;
    max-height:120px;
    object-fit:cover;
}
.ad-title {
    font-size:15px;font-weight:700;color:#111827;line-height:1.3;
}
.muted {font-size:12px;color:#6b7280;}
.badge {
    display:inline-block;padding:4px 8px;border-radius:999px;
    font-size:12px;font-weight:700;background:#eef2ff;color:#3730a3;
}
</style>
""", unsafe_allow_html=True)


def safe_float(v):
    try:
        return float(v)
    except:
        return 0.0


def safe_int(v):
    try:
        return int(v)
    except:
        return 0


def fetch_all_pages(url, params, max_pages=20):
    all_data = []
    page = 0
    while url and page < max_pages:
        res = requests.get(url, params=params)
        data = res.json()

        if "error" in data:
            st.error(data["error"]["message"])
            break

        all_data.extend(data.get("data", []))
        url = data.get("paging", {}).get("next")
        params = None
        page += 1

    return all_data


def extract_leads(actions):
    leads = 0
    for action in actions or []:
        action_type = action.get("action_type", "")
        if "lead" in action_type:
            leads += safe_int(action.get("value", 0))
    return leads


def score_row(row):
    cpl = row.get("CPL", 0)
    leads = row.get("Leads", 0)
    ctr = row.get("CTR", 0)
    cpc = row.get("CPC", 0)
    frequency = row.get("Frequency", 0)

    score = 0

    if 0 < cpl <= 5:
        score += 40
    elif cpl <= 10:
        score += 32
    elif cpl <= 20:
        score += 24
    elif cpl <= 40:
        score += 12

    if leads >= 1000:
        score += 25
    elif leads >= 500:
        score += 20
    elif leads >= 100:
        score += 15
    elif leads >= 30:
        score += 8

    if ctr >= 4:
        score += 20
    elif ctr >= 3:
        score += 15
    elif ctr >= 2:
        score += 10
    elif ctr >= 1:
        score += 5

    if 0 < cpc <= 2:
        score += 10
    elif cpc <= 4:
        score += 7
    elif cpc <= 7:
        score += 4

    if 0 < frequency <= 2.5:
        score += 5
    elif frequency <= 4:
        score += 3

    return min(score, 100)


def classify(score):
    if score >= 85:
        return "🟢 Elite Winner"
    if score >= 70:
        return "🟢 Winner"
    if score >= 55:
        return "🟡 Monitor"
    return "🔴 Weak"


def get_performance(start_date, end_date):
    url = f"https://graph.facebook.com/v25.0/act_{AD_ACCOUNT_ID}/insights"
    params = {
        "level": "ad",
        "fields": "ad_id,ad_name,spend,impressions,reach,frequency,cpm,cpc,ctr,actions",
        "time_range": f'{{"since":"{start_date}","until":"{end_date}"}}',
        "limit": 100,
        "access_token": ACCESS_TOKEN,
    }

    data = fetch_all_pages(url, params)
    rows = []

    for item in data:
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
            "Frequency": safe_float(item.get("frequency", 0)),
        })

    return pd.DataFrame(rows)


def get_creatives():
    url = f"https://graph.facebook.com/v25.0/act_{AD_ACCOUNT_ID}/ads"
    params = {
        "fields": "id,name,creative{id,name,thumbnail_url,image_url,video_id,object_story_spec,effective_object_story_id}",
        "limit": 100,
        "access_token": ACCESS_TOKEN,
    }

    data = fetch_all_pages(url, params)
    rows = []

    for item in data:
        creative = item.get("creative", {}) or {}
        video_id = creative.get("video_id", "")
        image_url = creative.get("image_url", "")
        thumbnail_url = creative.get("thumbnail_url", "")

        if video_id:
            creative_type = "🎥 Video"
        elif image_url:
            creative_type = "🖼️ Image"
        elif thumbnail_url:
            creative_type = "🖼️ Thumbnail"
        else:
            creative_type = "❓ Unknown"

        rows.append({
            "Ad ID": item.get("id"),
            "Creative ID": creative.get("id", ""),
            "Creative Name": creative.get("name", ""),
            "Thumbnail URL": thumbnail_url,
            "Image URL": image_url,
            "Video ID": video_id,
            "Creative Type": creative_type,
        })

    return pd.DataFrame(rows)


def preview_image(url):
    if not url or pd.isna(url) or str(url).lower() == "nan":
        st.markdown(
            "<div style='height:120px;background:#f3f4f6;border-radius:12px;display:flex;align-items:center;justify-content:center;color:#6b7280;font-size:12px;'>No Preview</div>",
            unsafe_allow_html=True
        )
        return

    try:
        st.image(url, use_container_width=True)
    except:
        st.markdown(
            "<div style='height:120px;background:#fef3c7;border-radius:12px;display:flex;align-items:center;justify-content:center;color:#92400e;font-size:12px;'>Preview Not Supported</div>",
            unsafe_allow_html=True
        )


def render_compact_card(row):
    preview_url = row.get("Thumbnail URL") or row.get("Image URL")

    st.markdown("<div class='creative-card'>", unsafe_allow_html=True)

    c1, c2 = st.columns([1, 2.2])

    with c1:
        preview_image(preview_url)

    with c2:
        st.markdown(f"<div class='ad-title'>{row.get('Ad Name','')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='muted'>{row.get('Creative Name','')}</div>", unsafe_allow_html=True)
        st.markdown(f"<span class='badge'>{row.get('Creative Type','Unknown')}</span>", unsafe_allow_html=True)
        st.write(f"**Score:** {safe_int(row.get('Winner Score', 0))}/100")
        st.write(f"**Status:** {row.get('Status','')}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Leads", f"{safe_int(row.get('Leads', 0)):,}")
    m2.metric("CPL", f"{safe_float(row.get('CPL', 0)):.2f}")
    m3.metric("CTR", f"{safe_float(row.get('CTR', 0)):.2f}%")
    m4.metric("CPC", f"{safe_float(row.get('CPC', 0)):.2f}")

    st.caption(f"Spend: {safe_float(row.get('Spend', 0)):,.0f} EGP")
    st.markdown("</div>", unsafe_allow_html=True)


st.title("🚀 Creative Intelligence Dashboard")
st.caption("Meta Ads Creative Performance Intelligence")

with st.sidebar:
    st.header("Filters")
    today = date.today()
    default_start = today - timedelta(days=30)

    start_date = st.date_input("Start Date", default_start)
    end_date = st.date_input("End Date", today)

    min_score = st.slider("Minimum Score", 0, 100, 70, 5)
    max_cards = st.slider("Cards Count", 6, 100, 30, 3)

    st.info("Score = CPL + Leads Volume + CTR + CPC + Frequency")

performance_df = get_performance(start_date, end_date)
creative_df = get_creatives()

if performance_df.empty:
    st.warning("No performance data returned from Meta API.")
else:
    df = performance_df.merge(creative_df, on="Ad ID", how="left")

    df["Winner Score"] = df.apply(score_row, axis=1)
    df["Status"] = df["Winner Score"].apply(classify)

    total_spend = df["Spend"].sum()
    total_leads = df["Leads"].sum()
    avg_cpl = total_spend / total_leads if total_leads > 0 else 0
    avg_ctr = df["CTR"].mean()
    avg_cpc = df["CPC"].mean()

    winners = df[df["Winner Score"] >= min_score].sort_values(
        ["Winner Score", "CPL"], ascending=[False, True]
    )

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Spend", f"{total_spend:,.0f} EGP")
    k2.metric("Leads", f"{total_leads:,}")
    k3.metric("Avg CPL", f"{avg_cpl:.2f} EGP")
    k4.metric("Avg CTR", f"{avg_ctr:.2f}%")
    k5.metric("Avg CPC", f"{avg_cpc:.2f} EGP")
    k6.metric("Selected", f"{len(winners):,}")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🏆 Top Creatives",
        "🟡 Monitor",
        "🔴 Weak",
        "📊 Full Table"
    ])

    with tab1:
        st.subheader("Top Creative Cards")

        selected = winners.head(max_cards)

        if selected.empty:
            st.warning("No creatives match this score.")
        else:
            for i in range(0, len(selected), 2):
                cols = st.columns(2)
                group = selected.iloc[i:i+2]

                for col, (_, row) in zip(cols, group.iterrows()):
                    with col:
                        render_compact_card(row)

    with tab2:
        monitor = df[(df["Winner Score"] >= 55) & (df["Winner Score"] < min_score)].sort_values(
            ["Winner Score", "CPL"], ascending=[False, True]
        )

        st.subheader("Monitor Creatives")
        for i in range(0, min(len(monitor), max_cards), 2):
            cols = st.columns(2)
            group = monitor.iloc[i:i+2]
            for col, (_, row) in zip(cols, group.iterrows()):
                with col:
                    render_compact_card(row)

    with tab3:
        weak = df[df["Winner Score"] < 55].sort_values("Spend", ascending=False)

        st.subheader("Weak / Low Score Creatives")
        for i in range(0, min(len(weak), max_cards), 2):
            cols = st.columns(2)
            group = weak.iloc[i:i+2]
            for col, (_, row) in zip(cols, group.iterrows()):
                with col:
                    render_compact_card(row)

    with tab4:
        st.subheader("All Ads Performance")

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
            "Status",
        ]

        final_df = df[display_cols].sort_values(
            ["Winner Score", "CPL"], ascending=[False, True]
        )

        st.dataframe(final_df, use_container_width=True)

        st.download_button(
            label="Download CSV",
            data=final_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="creative_intelligence_dashboard.csv",
            mime="text/csv"
        )

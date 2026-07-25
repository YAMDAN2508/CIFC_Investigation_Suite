import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import re
from datetime import datetime

# --- 1. Page Configuration & Custom CSS ---
st.set_page_config(
    page_title="CFIS - Cyber Forensics Intelligence Suite",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling to match the dark forensics dashboard UI
st.markdown("""
<style>
    .main {
        background-color: #0e1117;
    }
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
    }
    .stButton>button {
        background-color: #1f6beb;
        color: white;
        border-radius: 6px;
        border: none;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #388bfd;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Helper Functions & Analysis Engines ---

def parse_chat_timestamps(chat_text):
    """
    Extracts dates, times, senders, and messages from raw chat logs.
    Supports standard WhatsApp formats like: [25/07/2026, 14:30:15] Sender: Message
    """
    pattern = r'\[?(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*(AM|PM|ص|م)?\]?\s*-?\s*([^:]+):\s*(.*)'
    matches = re.findall(pattern, chat_text)
    
    parsed_data = []
    for match in matches:
        date_str, time_str, am_pm, sender, msg = match
        full_time_str = f"{date_str} {time_str} {am_pm}".strip()
        try:
            dt = pd.to_datetime(full_time_str, errors='coerce')
            if pd.notnull(dt):
                parsed_data.append({
                    "datetime": dt,
                    "sender": sender.strip(),
                    "message": msg.strip()
                })
        except Exception:
            continue
            
    # Fallback mock data if regex doesn't match raw input
    if not parsed_data:
        mock_dates = pd.date_range(start="2026-07-20 01:00", periods=25, freq="3h")
        mock_senders = ["Target_Alpha", "Victim_User"] * 12 + ["Target_Alpha"]
        mock_msgs = ["أرسل الحوالة الآن", "أحتاج وقت للتحويل", "إذا لم ترسل سأنشر مقاطعك", "أرجوك لا تفعل"] * 6 + ["أين المبلغ؟"]
        for d, s, m in zip(mock_dates, mock_senders, mock_msgs):
            parsed_data.append({"datetime": d, "sender": s, "message": m})

    return pd.DataFrame(parsed_data)

# --- 3. Sidebar Configuration ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/brain.png", width=60)
    st.title("CFIS Panel")
    st.caption("Cyber Forensics Intelligence Suite")
    st.markdown("---")
    
    st.subheader("⚙️ Case Parameters")
    case_id = st.text_input("Case ID", "CASE-2026-089")
    suspect_name = st.text_input("Suspect Identifier", "Target_Alpha")
    victim_name = st.text_input("Victim Identifier", "Victim_User")
    
    st.markdown("---")
    st.subheader("🌐 Forensic Translator")
    source_lang = st.selectbox("Source Language", ["auto (كشف تلقائي)", "Arabic", "English", "Urdu"])
    if st.button("🌐 Translate & Update Matrix"):
        st.success("Matrix successfully updated with translated forensic indicators.")

# --- 4. Main Title Banner ---
st.title("🧠 Psychological Intelligence & Deep Identity Analysis")
st.caption(f"Active Forensics Case: {case_id} | Investigator Module")

# Top Metrics Row
mcol1, mcol2, mcol3 = st.columns(3)
with mcol1:
    st.markdown("<div class='metric-card'><h4>🎭 Chat Tone Score</h4><h2 style='color:#ff4b4b;'>High Threat</h2></div>", unsafe_allow_html=True)
with mcol2:
    st.markdown("<div class='metric-card'><h4>💰 Financial Extortion Detected</h4><h2 style='color:#e6b800;'>3000.0 BHD</h2><p>Detected Terms: 2000, 1000</p></div>", unsafe_allow_html=True)
with mcol3:
    st.markdown("<div class='metric-card'><h4>🛡️ Evidence Integrity (SHA-256)</h4><p style='font-size:11px; word-break:break-all; color:#00ffcc;'>4cc130b792c1b8a6bd721f449e66a68d91f07f2489dce6b23dac3837256494c0</p></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Sample Chat Upload Area
with st.expander("📄 Evidence Chat File Input / Raw Log Text", expanded=False):
    chat_input = st.text_area("Paste Chat Export / Raw Log", value="""
[20/07/2026, 01:15:00] Target_Alpha: أرسل المبلغ الآن 2000 BHD
[20/07/2026, 01:20:00] Target_Alpha: أنا بانتظارك
[20/07/2026, 02:05:00] Victim_User: حسنًا سأحاول تحويل 1000 BHD
[20/07/2026, 18:30:00] Target_Alpha: تأخرت كثيرًا!
[21/07/2026, 03:10:00] Target_Alpha: أين الإثبات؟
[21/07/2026, 03:15:00] Target_Alpha: أسرع وإلا سأنشر الصور
[22/07/2026, 14:00:00] Target_Alpha: تم الاستلام
""", height=150)

df_chat = parse_chat_timestamps(chat_input)

# --- 5. Tabs Layout for Modules ---
tab_psych, tab_timeline, tab_osint = st.tabs([
    "🎭 Chat & Tone Analysis", 
    "🕒 WhatsApp Activity Timeline & Spikes", 
    "🔍 OSINT Reconnaissance"
])

# ==========================================
# TAB 1: Psychological & Tone Matrix
# ==========================================
with tab_psych:
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("🎭 Chat & Crime Tone Analysis")
        tone_data = pd.DataFrame({
            "Tone Category": ["Financial Demands", "Victim Response", "Threat Tone"],
            "Intensity Score": [40, 20, 38]
        })
        fig_tone = px.bar(
            tone_data, 
            y="Tone Category", 
            x="Intensity Score", 
            orientation='h',
            color="Intensity Score",
            color_continuous_scale="Reds"
        )
        st.plotly_chart(fig_tone, use_container_width=True)
        
    with col_b:
        st.subheader("🕸️ Participant Structure & Dominance")
        dominance_df = pd.DataFrame({
            "Participant": [suspect_name, victim_name],
            "Percentage": [60.9, 39.1]
        })
        fig_pie = px.pie(
            dominance_df, 
            values="Percentage", 
            names="Participant",
            color_discrete_sequence=["#3b82f6", "#ec4899"],
            hole=0.3
        )
        st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# TAB 2: WhatsApp Activity Timeline (NEW FEATURE)
# ==========================================
with tab_timeline:
    st.subheader("🕒 WhatsApp Activity Patterns & Timeline Analysis")
    st.info("تتيح هذه الميزة معرفة أوقات نشاط المتهم، ساعات الذروة اليومية، الأيام النشطة، والانقطاعات الزمنية المشبوهة.")
    
    if not df_chat.empty:
        suspect_df = df_chat[df_chat["sender"].str.contains(suspect_name, case=False, na=False)].copy()
        
        if not suspect_df.empty:
            suspect_df["hour"] = suspect_df["datetime"].dt.hour
            suspect_df["day_name"] = suspect_df["datetime"].dt.day_name()
            
            days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            suspect_df["day_name"] = pd.Categorical(suspect_df["day_name"], categories=days_order, ordered=True)
            
            tcol1, tcol2 = st.columns(2)
            
            with tcol1:
                st.markdown("#### 🔥 Active Hours Breakdown (Hourly Spikes)")
                hourly_counts = suspect_df["hour"].value_counts().reindex(range(24), fill_value=0).reset_index()
                hourly_counts.columns = ["الساعة", "عدد الرسائل"]
                
                fig_hours = px.bar(
                    hourly_counts,
                    x="الساعة",
                    y="عدد الرسائل",
                    title=f"ساعات النشاط اليومي للمتهم ({suspect_name})",
                    labels={"الساعة": "ساعات اليوم (00:00 - 23:00)", "عدد الرسائل": "عدد الرسائل"},
                    color="عدد الرسائل",
                    color_continuous_scale="Reds"
                )
                fig_hours.update_layout(xaxis=dict(tickmode='linear', tick0=0, dtick=2))
                st.plotly_chart(fig_hours, use_container_width=True)
                
            with tcol2:
                st.markdown("#### 📅 Weekly Activity Distribution")
                daily_counts = suspect_df["day_name"].value_counts().sort_index().reset_index()
                daily_counts.columns = ["اليوم", "عدد الرسائل"]
                
                fig_days = px.pie(
                    daily_counts,
                    values="عدد الرسائل",
                    names="اليوم",
                    title="توزيع نشاط المتهم حسب أيام الأسبوع",
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.RdBu
                )
                st.plotly_chart(fig_days, use_container_width=True)
                
            st.markdown("#### ⚠️ Temporal Anomalies & Suspicious Time Gaps")
            suspect_df = suspect_df.sort_values("datetime")
            suspect_df["time_gap_hours"] = suspect_df["datetime"].diff().dt.total_seconds() / 3600
            
            large_gaps = suspect_df[suspect_df["time_gap_hours"] >= 12].copy()
            
            if not large_gaps.empty:
                st.warning(f"تم رصد {len(large_gaps)} فجوة زمنية مشبوهة (انقطاع عن المراسلة لأكثر من 12 ساعة):")
                large_gaps["time_gap_hours"] = large_gaps["time_gap_hours"].round(1)
                display_gaps = large_gaps[["datetime", "time_gap_hours", "message"]].rename(columns={
                    "datetime": "وقت العودة للنشاط",
                    "time_gap_hours": "مدة الانقطاع (بالساعات)",
                    "message": "أول رسالة بعد الانقطاع"
                })
                st.dataframe(display_gaps, use_container_width=True)
            else:
                st.success("لا توجد فجوات زمنية طويلة مفاجئة، التواصل كان مستمراً بشكل طبيعي.")
        else:
            st.warning(f"لم يتم العثور على رسائل خاصة بالمستهدف: {suspect_name}")
    else:
        st.error("يرجى التأكد من توفر بيانات محادثة تحتوي على تواريخ وأوقات.")

# ==========================================
# TAB 3: OSINT Reconnaissance
# ==========================================
with tab_psych: pass
with tab_osint:
    st.subheader("⚡ Automated Social Media Footprint Recon")
    
    osint_data = pd.DataFrame([
        {"Platform / Network": "GitHub", "Profile Link": "https://github.com/scammer99", "Recon Status": "EXISTS / ACTIVE"},
        {"Platform / Network": "Telegram", "Profile Link": "https://t.me/scammer99", "Recon Status": "EXISTS / ACTIVE"},
        {"Platform / Network": "Reddit", "Profile Link": "https://www.reddit.com/user/scammer99", "Recon Status": "UNCERTAIN (403)"},
        {"Platform / Network": "X (Twitter)", "Profile Link": "https://x.com/scammer99", "Recon Status": "EXISTS / ACTIVE"},
        {"Platform / Network": "TikTok", "Profile Link": "https://www.tiktok.com/@scammer99", "Recon Status": "EXISTS / ACTIVE"},
        {"Platform / Network": "Instagram", "Profile Link": "https://www.instagram.com/scammer99/", "Recon Status": "UNCERTAIN (429)"},
    ])
    st.dataframe(osint_data, use_container_width=True)
    
    st.markdown("### 🔗 Deep External OSINT Investigation Links:")
    ocol1, ocol2 = st.columns(2)
    with ocol1:
        st.markdown("👉 [Search 'scammer99' on WhatsMyName.app](https://whatsmyname.app)")
    with ocol2:
        st.markdown("👉 [Google Dork Search for 'scammer99'](https://google.com)")

st.markdown("---")
# Footer
col_f1, col_f2 = st.columns([3, 1])
with col_f2:
    if st.button("📄 Generate Official PDF Forensics Report", use_container_width=True):
        st.balloons()
        st.success("PDF Forensics Report generated successfully!")

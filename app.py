import streamlit as st
import pandas as pd
import re
import json
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
import io
import base64
from datetime import datetime

# ==============================================================================
# 1. PAGE CONFIGURATION & INITIALIZATION
# ==============================================================================
st.set_page_config(
    page_title="CFIS - Cyber Forensic Intelligence System",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State Variables
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "parsed_df" not in st.session_state:
    st.session_state.parsed_df = pd.DataFrame()
if "extracted_iocs" not in st.session_state:
    st.session_state.extracted_iocs = {}
if "case_notes" not in st.session_state:
    st.session_state.case_notes = ""

# ==============================================================================
# 2. ADVANCED STYLES & CUSTOM CYBER FORENSIC THEME (CSS)
# ==============================================================================
st.markdown("""
<style>
    /* Dark Cyber Theme Imports & Color Variables */
    @import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;600&family=Inter:wght@300;400;600;700&display=swap');

    :root {
        --bg-main: #0b0f19;
        --bg-card: #161b22;
        --bg-card-hover: #1c2128;
        --border-color: #30363d;
        --accent-blue: #58a6ff;
        --accent-purple: #bc8cff;
        --accent-green: #3fb950;
        --accent-red: #f85149;
        --accent-amber: #d29922;
        --text-primary: #e6edf3;
        --text-secondary: #8b949e;
    }

    /* Overall Layout Overrides */
    .stApp {
        background-color: var(--bg-main);
        color: var(--text-primary);
        font-family: 'Inter', sans-serif;
    }

    /* Forensic Container Cards */
    .forensic-card {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        transition: all 0.2s ease-in-out;
    }
    
    .forensic-card:hover {
        border-color: #444c56;
    }

    .card-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--accent-blue);
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 8px;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        padding-bottom: 8px;
    }

    /* Custom Metric Display Badges */
    .metric-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: flex-start;
    }

    .metric-val {
        font-size: 2.2rem;
        font-weight: 700;
        font-family: 'Fira Code', monospace;
        line-height: 1.1;
    }

    .metric-lbl {
        font-size: 0.8rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin-top: 6px;
    }

    /* Cyber Code Block Displays */
    .ioc-box {
        font-family: 'Fira Code', monospace;
        background-color: #0d1117;
        border: 1px solid #21262d;
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 6px;
        font-size: 0.85rem;
        color: var(--accent-purple);
        word-break: break-all;
    }

    /* Threat Highlight Strip */
    .threat-banner {
        background: rgba(248, 81, 73, 0.12);
        border-left: 4px solid var(--accent-red);
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 15px;
    }

    .threat-title {
        color: var(--accent-red);
        font-weight: 600;
        font-size: 0.95rem;
    }

    /* Tabs Override */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }

    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        color: var(--text-secondary);
        font-weight: 600;
        padding: 0 20px;
    }

    .stTabs [aria-selected="true"] {
        background-color: var(--accent-blue) !important;
        color: #ffffff !important;
        border-color: var(--accent-blue) !important;
    }

    /* Custom Sidebar Aesthetics */
    section[data-testid="stSidebar"] {
        background-color: #0d1117;
        border-right: 1px solid var(--border-color);
    }

    /* RTL Text Helper Class */
    .rtl-block {
        direction: rtl;
        text-align: right;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 3. LOCALIZATION ENGINE (ENGLISH / ARABIC)
# ==============================================================================
TRANSLATIONS = {
    "English": {
        "app_title": "CFIS - Cyber Forensic Intelligence System",
        "app_subtitle": "Digital Evidence Parsing, IOC Threat Intelligence & Network Reconstruction",
        "sidebar_header": "⚙️ Forensic Toolkit & Operations",
        "select_lang": "Language / اللغة",
        "select_parser": "1. Evidence Source Format",
        "upload_label": "2. Import Forensic Dump File",
        "case_info_header": "📁 Case Metadata Configuration",
        "case_id_ph": "e.g., CASE-2026-BH-0091",
        "investigator_ph": "e.g., Det. H. Al-Mansoori",
        "analyze_btn": "🚀 Run Deep Forensic Extraction",
        "stats_messages": "Total Processed Messages",
        "stats_actors": "Identified Participants",
        "stats_threats": "Extortion / Threat Events",
        "stats_iocs": "Extracted Technical IOCs",
        "tab_overview": "📊 Dashboard & Intelligence Overview",
        "tab_network": "🕸️ Social Network Graph",
        "tab_iocs": "🔍 Technical IOC Deep Dive",
        "tab_chat_log": "📜 Evidence Message Registry",
        "tab_export": "📑 Case Audit & Report Generator",
        "card_timeline": "📈 Messaging Velocity & Timeline Distribution",
        "card_speaker_dist": "🎯 Participant Structure & Dominance",
        "card_ioc_summary": "🏷️ Extracted Intelligence Indicators (IOC Summary)",
        "card_network_title": "🌐 Actor Relational Map & Interaction Topography",
        "card_chat_title": "💬 Complete Extracted Message Ledger",
        "filter_flagged": "⚠️ Show Only Flagged Extortion/Threat Messages",
        "search_ph": "Search message body, handles, IBANs, phone numbers...",
        "no_data": "No forensic evidence file currently loaded. Please upload a file via the sidebar.",
        "case_notes_lbl": "Investigator Assessment & Case Notes",
        "download_csv": "📥 Export Clean Evidence Stream (CSV)",
        "download_pdf_rep": "📄 Download Executive Intelligence Summary (PDF/TXT)",
    },
    "Arabic": {
        "app_title": "منصة CFIS للتحقيق والجنائيات الرقمية",
        "app_subtitle": "معالجة واستخراج الأدلة الرقمية، تحليل شبكات الابتزاز، واستخراج المؤشرات الجنائية",
        "sidebar_header": "⚙️ أدوات التحقيق والتشغيل",
        "select_lang": "Language / اللغة",
        "select_parser": "1. صيغة مصدر الأدلة الرقمية",
        "upload_label": "2. رفع ملف التفريغ الجنائي",
        "case_info_header": "📁 بيانات وضوابط القضية",
        "case_id_ph": "مثال: CASE-2026-BH-0091",
        "investigator_ph": "مثال: المحقق ح. المنصوري",
        "analyze_btn": "🚀 بدء التحليل والجرد الجنائي العميق",
        "stats_messages": "إجمالي الرسائل المحللة",
        "stats_actors": "الأطراف والأشخاص المحددين",
        "stats_threats": "أحداث التهديد والابتزاز",
        "stats_iocs": "المؤشرات الجنائية المستخرجة",
        "tab_overview": "📊 لوحة التحليل والاستخبار الرقمي",
        "tab_network": "🕸️ مخطط الشبكة والعلاقات",
        "tab_iocs": "🔍 فحص المؤشرات الفنية (IOCs)",
        "tab_chat_log": "📜 السجل الجنائي الكامل للرسائل",
        "tab_export": "📑 تقرير القضية والتصدير الجنائي",
        "card_timeline": "📈 التسلسل الزمني وكثافة التراسل",
        "card_speaker_dist": "🎯 توزيع المشاركة والهيمنة",
        "card_ioc_summary": "🏷️ ملخص المؤشرات الرقمية (IOCs)",
        "card_network_title": "🌐 الخريطة التفاعلية للشبكة والأطراف",
        "card_chat_title": "💬 السجل المفرغ للرسائل المحللة",
        "filter_flagged": "⚠️ عرض رسائل الابتزاز والتهديد المحددة فقط",
        "search_ph": "بحث في نص الرسالة، الحسابات، الآيبان، أرقام الهواتف...",
        "no_data": "لا يوجد ملف أدلة جنائية محمل حالياً. يرجى رفع ملف من الشريط الجانبي.",
        "case_notes_lbl": "ملاحظات وتقييم المحقق الجنائي",
        "download_csv": "📥 تصدير سجل الرسائل (CSV)",
        "download_pdf_rep": "📄 تحميل التقرير التنفيذي المعتمد (PDF/TXT)",
    }
}

# ==============================================================================
# 4. REGULAR EXPRESSIONS & FORENSIC PATTERN ENGINE
# ==============================================================================
FORENSIC_PATTERNS = {
    "Phone Numbers": r'\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}',
    "IBAN / Bank Accounts": r' [A-Z]{2}\d{2}[A-Z0-9]{11,30} ',
    "Crypto Wallets (BTC)": r' (bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39} ',
    "IP Addresses": r' (?:\d{1,3}\.){3}\d{1,3} ',
    "URLs / Malicious Domains": r'https?://[^\s]+',
    "Usernames / Social Handles": r'@[a-zA-Z0-9_]+',
    "Email Addresses": r' [A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,} '
}

EXTORTION_KEYWORDS = [
    'fadiha', 'فضاحة', 'فضايح', 'صور', 'اخترقت', 'تحويل', 'فلوس', 'ارسل', 'حسابك',
    'pay', 'money', 'photos', 'publish', 'blackmail', 'hacked', 'iban', 'cash', 'transfer',
    'خايف', 'ارجوك', 'تكفى', 'انستغرام', 'تويتر', 'تليجرام', 'فضيحة', 'سيرفر', 'تهديد'
]

# ==============================================================================
# 5. FORENSIC PARSING & PROCESSING FUNCTIONS
# ==============================================================================
def extract_all_iocs(text_body):
    """Parses text body for technical indicators of compromise (IOCs)."""
    results = {}
    for label, pattern in FORENSIC_PATTERNS.items():
        matches = list(set(re.findall(pattern, text_body, re.IGNORECASE)))
        if matches:
            results[label] = matches
    return results

def evaluate_threat_score(text):
    """Evaluates extortion risk based on keyword occurrences and length."""
    if not isinstance(text, str):
        return False, 0
    text_lower = text.lower()
    matches = [kw for kw in EXTORTION_KEYWORDS if kw in text_lower]
    score = len(matches)
    is_threat = score > 0
    return is_threat, score

def parse_whatsapp_txt(content_str):
    """Parses standard & forensic exported WhatsApp text logs."""
    # Matches patterns like: [12/04/2026, 14:10:05] Name (+123): Message
    pattern = r'\[?(\d{2}/\d{2}/\d{4},\s\d{2}:\d{2}:\d{2})\]?\s([^:]+):\s(.*)'
    lines = content_str.split(' ')
    parsed_records = []

    for line in lines:
        line = line.strip()
        match = re.match(pattern, line)
        if match:
            raw_time, sender, msg_text = match.groups()
            is_threat, threat_score = evaluate_threat_score(msg_text)
            parsed_records.append({
                'Timestamp': raw_time,
                'Sender': sender.strip(),
                'Message': msg_text.strip(),
                'Threat_Flag': is_threat,
                'Threat_Score': threat_score
            })

    df = pd.DataFrame(parsed_records)
    if not df.empty:
        df['Datetime'] = pd.to_datetime(df['Timestamp'], format='%d/%m/%Y, %H:%M:%S', errors='coerce')
    return df

def parse_instagram_json(content_str):
    """Parses standard Instagram Direct Message JSON exports."""
    try:
        data = json.loads(content_str)
        messages = data.get('messages', [])
        records = []
        
        for msg in messages:
            sender = msg.get('sender_name', 'Unknown')
            text = msg.get('content', '')
            ts_ms = msg.get('timestamp_ms', 0)
            dt_str = pd.to_datetime(ts_ms, unit='ms').strftime('%d/%m/%Y, %H:%M:%S')
            is_threat, threat_score = evaluate_threat_score(text)
            
            records.append({
                'Timestamp': dt_str,
                'Sender': sender,
                'Message': text,
                'Threat_Flag': is_threat,
                'Threat_Score': threat_score
            })
            
        df = pd.DataFrame(records)
        if not df.empty:
            df['Datetime'] = pd.to_datetime(df['Timestamp'], format='%d/%m/%Y, %H:%M:%S', errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error parsing Instagram JSON: {e}")
        return pd.DataFrame()

# ==============================================================================
# 6. APPLICATION SIDEBAR CONTROLS
# ==============================================================================
def render_sidebar():
    st.sidebar.title("🛡️ CFIS Control Center")
    
    # Language Selection
    selected_lang = st.sidebar.radio("Language / اللغة", ["English", "Arabic"])
    tx = TRANSLATIONS[selected_lang]
    
    st.sidebar.markdown("---")
    st.sidebar.subheader(tx["sidebar_header"])
    
    parser_type = st.sidebar.selectbox(
        tx["select_parser"],
        ["WhatsApp (.txt)", "Instagram DMs (.json)", "Generic Forensic TXT Dump"]
    )
    
    uploaded_file = st.sidebar.file_uploader(
        tx["upload_label"],
        type=["txt", "json"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.subheader(tx["case_info_header"])
    case_id = st.sidebar.text_input("Case Reference ID", placeholder=tx["case_id_ph"])
    investigator = st.sidebar.text_input("Lead Investigator", placeholder=tx["investigator_ph"])
    
    run_btn = st.sidebar.button(tx["analyze_btn"], use_container_width=True, type="primary")
    
    return selected_lang, tx, parser_type, uploaded_file, case_id, investigator, run_btn

# ==============================================================================
# 7. MAIN EXECUTION WORKFLOW
# ==============================================================================
def main():
    lang, tx, parser_type, uploaded_file, case_id, investigator, run_btn = render_sidebar()
    
    # Main Header Display
    st.title(tx["app_title"])
    st.caption(f"{tx['app_subtitle']} | Case: `{case_id if case_id else 'UNASSIGNED'}` | Lead: `{investigator if investigator else 'ADMIN'}`")
    st.markdown("---")

    # File Ingestion Logic
    if run_btn and uploaded_file is not None:
        raw_content = uploaded_file.getvalue().decode("utf-8", errors="ignore")
        
        if "WhatsApp" in parser_type or "Generic" in parser_type:
            df_parsed = parse_whatsapp_txt(raw_content)
        else:
            df_parsed = parse_instagram_json(raw_content)
            
        if not df_parsed.empty:
            st.session_state.parsed_df = df_parsed
            
            # Combine all message texts for complete IOC extraction
            full_corpus = " ".join(df_parsed['Message'].dropna().tolist())
            st.session_state.extracted_iocs = extract_all_iocs(full_corpus)
            st.session_state.analysis_done = True
            st.success("✅ Forensic analysis completed successfully!")
        else:
            st.error("Failed to parse file. Please verify format compatibility.")

    # Render Dashboard if Analysis Data Exists
    if st.session_state.analysis_done and not st.session_state.parsed_df.empty:
        df = st.session_state.parsed_df
        iocs = st.session_state.extracted_iocs

        # Metrics Row
        total_msgs = len(df)
        total_actors = df['Sender'].nunique()
        total_threats = df['Threat_Flag'].sum()
        total_iocs_count = sum(len(v) for v in iocs.values())

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.markdown(f"""
            <div class='forensic-card metric-container'>
                <div class='metric-val' style='color: var(--accent-blue);'>{total_msgs}</div>
                <div class='metric-lbl'>{tx['stats_messages']}</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"""
            <div class='forensic-card metric-container'>
                <div class='metric-val' style='color: var(--accent-purple);'>{total_actors}</div>
                <div class='metric-lbl'>{tx['stats_actors']}</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col3:
            st.markdown(f"""
            <div class='forensic-card metric-container'>
                <div class='metric-val' style='color: var(--accent-red);'>{total_threats}</div>
                <div class='metric-lbl'>{tx['stats_threats']}</div>
            </div>
            """, unsafe_allow_html=True)
        with m_col4:
            st.markdown(f"""
            <div class='forensic-card metric-container'>
                <div class='metric-val' style='color: var(--accent-amber);'>{total_iocs_count}</div>
                <div class='metric-lbl'>{tx['stats_iocs']}</div>
            </div>
            """, unsafe_allow_html=True)

        # Tabs Layout
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            tx["tab_overview"],
            tx["tab_network"],
            tx["tab_iocs"],
            tx["tab_chat_log"],
            tx["tab_export"]
        ])

        # ==============================================================================
        # TAB 1: OVERVIEW & CHARTS
        # ==============================================================================
        with tab1:
            c1, c2 = st.columns([1.6, 1])

            # Chart 1: Timeline Velocity
            with c1:
                st.markdown(f"<div class='forensic-card'><div class='card-header'>{tx['card_timeline']}</div>", unsafe_allow_html=True)
                if 'Datetime' in df.columns and not df['Datetime'].isna().all():
                    df_time = df.dropna(subset=['Datetime']).sort_values('Datetime')
                    df_resampled = df_time.groupby(pd.Grouper(key='Datetime', freq='1h')).size().reset_index(name='Message Count')
                    
                    fig_timeline = px.line(
                        df_resampled, x='Datetime', y='Message Count',
                        markers=True, color_discrete_sequence=['#58a6ff']
                    )
                    fig_timeline.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        font_color="#e6edf3", height=380,
                        margin=dict(t=10, b=10, l=10, r=10),
                        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#21262d')
                    )
                    st.plotly_chart(fig_timeline, use_container_width=True)
                else:
                    st.info("Timestamp temporal analysis unavailable for this stream format.")
                st.markdown("</div>", unsafe_allow_html=True)

            # Chart 2: Participant Dominance (Pie Chart with Legend at Bottom)
            with c2:
                st.markdown(f"<div class='forensic-card'><div class='card-header'>{tx['card_speaker_dist']}</div>", unsafe_allow_html=True)
                df_senders = df['Sender'].value_counts().reset_index()
                df_senders.columns = ['Speaker', 'Messages']

                fig_speaker = px.pie(
                    df_senders, names='Speaker', values='Messages',
                    color_discrete_sequence=px.colors.qualitative.Dark24
                )
                
                # -------------------------------------------------------------
                # PERFECTED PIE CHART LAYOUT: Legend moved to bottom horizontally
                # -------------------------------------------------------------
                fig_speaker.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color="#e6edf3",
                    margin=dict(t=20, b=20, l=10, r=10),
                    height=380,
                    legend=dict(
                        orientation="h",
                        yanchor="top",
                        y=-0.15,
                        xanchor="center",
                        x=0.5
                    )
                )
                st.plotly_chart(fig_speaker, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

            # Quick IOC Summary Panel
            st.markdown(f"<div class='forensic-card'><div class='card-header'>{tx['card_ioc_summary']}</div>", unsafe_allow_html=True)
            if iocs:
                cols = st.columns(len(iocs))
                for idx, (cat, items) in enumerate(iocs.items()):
                    with cols[idx % len(cols)]:
                        st.markdown(f"**{cat}**")
                        for item in items[:4]:
                            st.markdown(f"<div class='ioc-box'>{item}</div>", unsafe_allow_html=True)
                        if len(items) > 4:
                            st.caption(f"+ {len(items)-4} more...")
            else:
                st.info("No network/financial IOCs automatically extracted.")
            st.markdown("</div>", unsafe_allow_html=True)

        # ==============================================================================
        # TAB 2: NETWORK TOPOLOGY GRAPH
        # ==============================================================================
        with tab2:
            st.markdown(f"<div class='forensic-card'><div class='card-header'>{tx['card_network_title']}</div>", unsafe_allow_html=True)
            
            # Construct Relational Network Graph using NetworkX
            G = nx.Graph()
            speakers = df['Sender'].unique().tolist()
            for s in speakers:
                G.add_node(s, type='actor')

            # Link actors to extracted IOC items found in their messages
            for _, row in df.iterrows():
                sender = row['Sender']
                msg = row['Message']
                row_iocs = extract_all_iocs(msg)
                for cat, items in row_iocs.items():
                    for item in items:
                        if not G.has_node(item):
                            G.add_node(item, type='ioc', category=cat)
                        G.add_edge(sender, item)

            pos = nx.spring_layout(G, k=0.5, seed=42)

            edge_x = []
            edge_y = []
            for edge in G.edges():
                x0, y0 = pos[edge[0]]
                x1, y1 = pos[edge[1]]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

            edge_trace = go.Scatter(
                x=edge_x, y=edge_y,
                line=dict(width=1, color='#30363d'),
                hoverinfo='none', mode='lines'
            )

            node_x = []
            node_y = []
            node_text = []
            node_color = []
            node_size = []

            for node in G.nodes():
                x, y = pos[node]
                node_x.append(x)
                node_y.append(y)
                node_text.append(str(node))
                if G.nodes[node].get('type') == 'actor':
                    node_color.append('#58a6ff')
                    node_size.append(24)
                else:
                    node_color.append('#bc8cff')
                    node_size.append(14)

            node_trace = go.Scatter(
                x=node_x, y=node_y,
                mode='markers+text',
                hoverinfo='text',
                text=node_text,
                textposition="bottom center",
                marker=dict(
                    color=node_color,
                    size=node_size,
                    line=dict(width=2, color='#ffffff')
                )
            )

            fig_net = go.Figure(data=[edge_trace, node_trace],
                layout=go.Layout(
                    showlegend=False,
                    hovermode='closest',
                    margin=dict(b=0, l=0, r=0, t=0),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                    height=550
                )
            )
            st.plotly_chart(fig_net, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        # ==============================================================================
        # TAB 3: IOC DEEP DIVE
        # ==============================================================================
        with tab3:
            st.markdown(f"<div class='forensic-card'><div class='card-header'>{tx['tab_iocs']}</div>", unsafe_allow_html=True)
            if iocs:
                for cat, items in iocs.items():
                    st.subheader(f"📌 {cat}")
                    ioc_df = pd.DataFrame(items, columns=['Extracted Intelligence Value'])
                    st.dataframe(ioc_df, use_container_width=True)
            else:
                st.info("No indicators found.")
            st.markdown("</div>", unsafe_allow_html=True)

        # ==============================================================================
        # TAB 4: CHAT EVIDENCE STREAM
        # ==============================================================================
        with tab4:
            st.markdown(f"<div class='forensic-card'><div class='card-header'>{tx['card_chat_title']}</div>", unsafe_allow_html=True)
            
            sc1, sc2 = st.columns([3, 1])
            with sc1:
                search_q = st.text_input("Filter Stream", placeholder=tx["search_ph"], label_visibility="collapsed")
            with sc2:
                only_threats = st.checkbox(tx["filter_flagged"])

            filtered_df = df.copy()
            if only_threats:
                filtered_df = filtered_df[filtered_df['Threat_Flag'] == True]
            if search_q:
                filtered_df = filtered_df[filtered_df['Message'].str.contains(search_q, case=False, na=False)]

            st.dataframe(
                filtered_df[['Timestamp', 'Sender', 'Message', 'Threat_Flag']],
                column_config={
                    "Timestamp": st.column_config.TextColumn("Timestamp", width="medium"),
                    "Sender": st.column_config.TextColumn("Actor / Sender", width="medium"),
                    "Message": st.column_config.TextColumn("Message Body", width="large"),
                    "Threat_Flag": st.column_config.CheckboxColumn("Extortion Flag", width="small")
                },
                use_container_width=True,
                hide_index=True
            )
            st.markdown("</div>", unsafe_allow_html=True)

        # ==============================================================================
        # TAB 5: CASE REPORT GENERATOR
        # ==============================================================================
        with tab5:
            st.markdown(f"<div class='forensic-card'><div class='card-header'>{tx['tab_export']}</div>", unsafe_allow_html=True)
            
            notes = st.text_area(tx["case_notes_lbl"], value=st.session_state.case_notes, height=150)
            st.session_state.case_notes = notes

            rc1, rc2 = st.columns(2)
            
            # CSV Download Button
            with rc1:
                csv_data = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=tx["download_csv"],
                    data=csv_data,
                    file_name=f"CFIS_Evidence_Export_{case_id if case_id else 'DUMP'}.csv",
                    mime="text/csv",
                    use_container_width=True
                )

            # Executive Summary Export
            with rc2:
                summary_text = f"""
================================================================================
           CYBER FORENSIC INTELLIGENCE SYSTEM (CFIS) - EXECUTIVE REPORT
================================================================================
Case ID: {case_id if case_id else 'N/A'}
Lead Investigator: {investigator if investigator else 'N/A'}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

[1. STATISTICAL SUMMARY]
- Total Messages Processed: {total_msgs}
- Identified Actors: {total_actors} ({', '.join(df['Sender'].unique().tolist())})
- Threat/Extortion Incidents: {total_threats}
- Total Technical IOCs: {total_iocs_count}

[2. EXTRACTED IOC INDICATORS]
{json.dumps(iocs, indent=2)}

[3. INVESTIGATOR NOTES]
{notes}
================================================================================
                """
                st.download_button(
                    label=tx["download_pdf_rep"],
                    data=summary_text.encode('utf-8'),
                    file_name=f"CFIS_Executive_Report_{case_id if case_id else 'DUMP'}.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.info(tx["no_data"])

if __name__ == "__main__":
    main()

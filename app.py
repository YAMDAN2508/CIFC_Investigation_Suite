import streamlit as st
import pandas as pd
import plotly.express as px
import re
import sqlite3
import hashlib
from datetime import datetime
from fpdf import FPDF
import io

# ==============================================================================
# CSS CUSTOM STYLING (THEME & TYPOGRAPHY)
# ==============================================================================
def apply_custom_theme():
    st.markdown("""
        <style>
            /* خلفية التطبيق العامة وتنسيق النصوص */
            .stApp {
                background-color: #0d1117;
                color: #c9d1d9;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            
            /* تحسين الهيدر والعناوين */
            h1 {
                color: #58a6ff !important;
                font-weight: 700 !important;
                text-shadow: 0px 0px 10px rgba(88, 166, 255, 0.2);
            }
            h2, h3, h4 {
                color: #f0f6fc !important;
                font-weight: 600 !important;
            }
            
            /* تنسيق التبويبات (Tabs) */
            .stTabs [data-baseweb="tab-list"] {
                gap: 10px;
                background-color: #161b22;
                padding: 8px;
                border-radius: 10px;
                border: 1px solid #30363d;
            }
            .stTabs [data-baseweb="tab"] {
                height: 45px;
                white-space: pre;
                background-color: transparent;
                border-radius: 6px;
                color: #8b949e;
                font-weight: bold;
                transition: all 0.3s ease;
            }
            .stTabs [data-baseweb="tab"]:hover {
                color: #58a6ff;
                background-color: #21262d;
            }
            .stTabs [aria-selected="true"] {
                background-color: #1f6feb !important;
                color: #ffffff !important;
                border-radius: 6px;
            }
            
            /* تصميم البطاقات الجنائية (Forensic Cards) */
            .forensic-card {
                background-color: #161b22;
                border: 1px solid #30363d;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                margin-bottom: 15px;
            }
            
            /* أزرار مخصصة وتفاعلية */
            .stButton>button {
                background: linear-gradient(135deg, #1f6feb 0%, #115293 100%) !important;
                color: white !important;
                border: none !important;
                padding: 10px 24px !important;
                border-radius: 8px !important;
                font-weight: 600 !important;
                transition: all 0.3s ease !important;
                width: 100%;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            .stButton>button:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(31, 111, 235, 0.4) !important;
            }
            
            /* تنسيق الشريط الجانبي (Sidebar) */
            section[data-testid="stSidebar"] {
                background-color: #090d13 !important;
                border-right: 1px solid #30363d;
            }
            
            /* تنسيق الجداول وعناصر الإدخال */
            .stDataFrame, .stTable {
                border: 1px solid #30363d;
                border-radius: 8px;
                overflow: hidden;
            }
        </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 1. DATABASE SETUP & CASE VAULT MANAGEMENT
# ==============================================================================
def init_db():
    conn = sqlite3.connect('cfis_local_vault.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historical_markers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator TEXT UNIQUE,
            indicator_type TEXT,
            case_number TEXT,
            officer_assigned TEXT,
            date_logged TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cases_archive (
            case_number TEXT PRIMARY KEY,
            officer_assigned TEXT,
            suspect_name TEXT,
            file_hash TEXT,
            chat_content TEXT,
            date_saved TEXT
        )
    ''')
    mock_data = [
        ('BH12BBAN00000000123456', 'IBAN', '2026/CID/894', 'Lt. Jasim', '2026-04-12'),
        ('+97333123456', 'Phone', '2026/CID/412', 'Sgt. Ali', '2026-05-19'),
        ('scammer99@gmail.com', 'Email', '2026/CID/894', 'Lt. Jasim', '2026-04-12'),
        ('1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa', 'Crypto', '2026/CID/102', 'Capt. Reem', '2026-06-01'),
        ('192.168.1.105', 'IP Address', '2026/CID/711', 'Lt. Dana', '2026-07-10')
    ]
    try:
        cursor.executemany('INSERT OR IGNORE INTO historical_markers (indicator, indicator_type, case_number, officer_assigned, date_logged) VALUES (?, ?, ?, ?, ?)', mock_data)
        conn.commit()
    except sqlite3.Error:
        pass
    finally:
        conn.close()

init_db()

def check_cross_case(indicator):
    conn = sqlite3.connect('cfis_local_vault.db')
    cursor = conn.cursor()
    cursor.execute("SELECT case_number, officer_assigned FROM historical_markers WHERE indicator = ?", (indicator,))
    result = cursor.fetchone()
    conn.close()
    return result

def add_manual_indicator(ind, ind_type, case_num, officer):
    conn = sqlite3.connect('cfis_local_vault.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO historical_markers (indicator, indicator_type, case_number, officer_assigned, date_logged) VALUES (?, ?, ?, ?, ?)",
                       (ind, ind_type, case_num, officer, datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def get_all_indicators():
    conn = sqlite3.connect('cfis_local_vault.db')
    df = pd.read_sql_query("SELECT * FROM historical_markers ORDER BY id DESC", conn)
    conn.close()
    return df

def save_full_case(case_num, officer, suspect, f_hash, content):
    conn = sqlite3.connect('cfis_local_vault.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO cases_archive (case_number, officer_assigned, suspect_name, file_hash, chat_content, date_saved)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (case_num, officer, suspect, f_hash, content, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()

def load_full_case(case_num):
    conn = sqlite3.connect('cfis_local_vault.db')
    cursor = conn.cursor()
    cursor.execute("SELECT chat_content, officer_assigned, suspect_name, file_hash FROM cases_archive WHERE case_number = ?", (case_num,))
    result = cursor.fetchone()
    conn.close()
    return result

def calculate_sha256(bytes_data):
    return hashlib.sha256(bytes_data).hexdigest()

# ==============================================================================
# 2. ADVANCED DATA ANALYTICS & THREAT ENGINES
# ==============================================================================
def analyze_chat_threat_score(text, lang_choice):
    high_risk_words = ['تهديد', 'ابتزاز', 'فلوس', 'حساب', 'تحويل', 'اخترقت', 'اطرش', 'صورك', 'fadiha', 'فضيحة', 'money', 'blackmail', 'hack', 'transfer', 'wire', 'scam']
    med_risk_words = ['رابط', 'يوزر', 'باسورد', 'ايميل', 'كود', 'واتساب', 'link', 'password', 'code', 'verify', 'user', 'whatsapp']
    
    high_hits = sum(1 for w in high_risk_words if w in text.lower())
    med_hits = sum(1 for w in med_risk_words if w in text.lower())
    
    score = (high_hits * 15) + (med_hits * 7)
    score = min(score, 100)
    
    if score >= 60:
        return score, "CRITICAL RISK 🚨" if lang_choice == "English" else "مستوى خطر حرج (شبهة ابتزاز/احتيال) 🚨"
    elif score >= 25:
        return score, "MEDIUM RISK ⚠️" if lang_choice == "English" else "مستوى خطر متوسط ⚠️"
    return score, "LOW RISK ✅" if lang_choice == "English" else "مستوى خطر منخفض ✅"

def analyze_sentiment_and_tone(text):
    threat_words = ['تهديد', 'ابتزاز', 'فضيحة', 'بفضحك', 'انشر', 'صورك', 'blackmail', 'expose', 'threat']
    fear_words = ['خايف', 'ارجوك', 'لا تنشر', 'ستر', 'تكفى', 'please', 'dont', 'afraid', 'stop']
    financial_words = ['تحويل', 'فلوس', 'دينار', 'حساب', 'كاش', 'money', 'cash', 'pay', 'transfer']
    
    t_count = sum(1 for w in threat_words if w in text.lower())
    f_count = sum(1 for w in fear_words if w in text.lower())
    m_count = sum(1 for w in financial_words if w in text.lower())
    total = t_count + f_count + m_count if (t_count + f_count + m_count) > 0 else 1
    
    return {
        "Threat Tone": round((t_count/total)*100, 1),
        "Victim Response": round((f_count/total)*100, 1),
        "Financial Demands": round((m_count/total)*100, 1)
    }

def extract_financial_amounts(text):
    amounts = re.findall(r'\b(\d+(?:\.\d+)?)\s*(?:دينار|بحريني|BD|BHD|dollar|\$|euro)\b', text.lower())
    total_extracted = sum(float(amt) for amt in amounts)
    return amounts, total_extracted

def analyze_url_or_ip(item, lang_choice):
    is_ip = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', item)
    if is_ip:
        return ("SUSPICIOUS IP 🌐" if lang_choice == "English" else "IP مشبوه 🌐"), 70, ("Local Sandbox Routing Flagged" if lang_choice == "English" else "تم رصد محاولة توجيه مشبوهة")
    suspicious_keywords = ['login', 'verify', 'update', 'bank', 'secure', 'free', 'gift', 'crypto', 'تحويل', 'تأمين']
    score = 0
    reasons = []
    for word in suspicious_keywords:
        if word in item.lower():
            score += 25
            reasons.append(f"Keyword '{word}'")
    if len(item) > 50:
        score += 20
        reasons.append("Long URL" if lang_choice == "English" else "رابط طويل مريب")
    if score >= 50:
        return ("HIGH RISK 🚨" if lang_choice == "English" else "خطورة عالية 🚨"), min(score, 100), ", ".join(reasons)
    return ("SAFE ✅" if lang_choice == "English" else "آمن ✅"), score, "-"

# ==============================================================================
# 3. BILINGUAL LEXICON (WITH DYNAMIC SEARCH PLACEHOLDERS)
# ==============================================================================
LEXICON = {
    "English": {
        "title": "🛡️ Chat-Forensics Intelligence Suite (CFIS)",
        "sub": "CID Anti-Electronic Crime Directorate | Advanced Forensic Triage V5",
        "sb_header": "📁 Investigative Case Metadata",
        "sb_case": "Official Case Number:",
        "sb_officer": "Investigating Officer Name / Rank:",
        "sb_suspect": "Suspect Identifier / Alias:",
        "upload_lbl": "Upload Exported Chat Logs (.txt format)",
        "ingest": "📦 Ingesting evidence stream...",
        "success": "✅ Advanced Forensic Triaging Sequence Completed.",
        "charts_title": "📊 Activity & Behavioral Timeline Tracking",
        "chart_h_title": "Suspect Hourly Activity Spikes (Peak Operations)",
        "chart_d_title": "Operational Activity Split per Calendar Day",
        "art_title": "🔍 High-Value Artifact Extraction & Threat Intel Matching",
        "tab_bank": "🏦 Banking Indicators",
        "tab_phone": "📞 Telephony & Comms",
        "tab_crypto": "🪙 Crypto Wallets",
        "tab_url": "🔗 URL & IP Scanner",
        "tab_search": "🕵️‍♂️ Contextual Search",
        "tab_osint": "🌐 OSINT Username Tracker",
        "tab_vault": "📁 Case Vault & Archive Manager",
        "pdf_btn": "Generate Official PDF Forensics Report",
        "search_lbl": "Enter keyword or indicator to search in full conversation:",
        "search_placeholder": "e.g., blackmail, transfer, hack, حساب, ابتزاز",
        "vault_add_hdr": "Add New Forensic Indicator Manually",
        "vault_tbl_hdr": "Live Central Database Records Archive",
        "col_iban": "IBAN Account Number",
        "col_status": "Cross-Case Match Status",
        "col_phone": "Phone Number",
        "col_match": "Database Match",
        "col_email": "Email Address",
        "col_crypto": "Crypto Wallet Address",
        "col_url": "Extracted URL / IP",
        "col_risk": "Risk Assessment",
        "col_score": "Threat Score",
        "col_flags": "Risk Indicators Found"
    },
    "العربية": {
        "title": "🛡️ المنظومة الذكية لتحليل أدلة المحادثات الرقمية (CFIS)",
        "sub": "الإدارة العامة لمكافحة الفساد والأمن الاقتصادي والإلكتروني | إدارة مكافحة الجرائم الإلكترونية",
        "sb_header": "📁 بيانات ملف القضية الجنائية",
        "sb_case": "رقم القضية الرسمي:",
        "sb_officer": "اسم ورتبة ضابط التحقيق:",
        "sb_suspect": "هوية / اسم الشهرة للمشتبه به:",
        "upload_lbl": "رفع سجلات المحادثات المصدرة (صيغة .txt)",
        "ingest": "📦 جاري فحص واستخراج سلسلة الأدلة...",
        "success": "✅ تم الانتهاء من عملية الفرز والتحليل الجنائي المتقدم بنجاح.",
        "charts_title": "📊 تتبع وتحليل السلوك الزمني والنشاط",
        "chart_h_title": "ساعات ذروة نشاط المشتبه به (النمط التشغيلي)",
        "chart_d_title": "توزيع حجم العمليات على أيام الأسبوع",
        "art_title": "🔍 استخراج الأدلة الرقمية ومطابقة الاستخبارات الجنائية",
        "tab_bank": "🏦 المؤشرات البنكية",
        "tab_phone": "📞 الاتصالات والهواتف",
        "tab_crypto": "🪙 المحافظ الرقمية",
        "tab_url": "🔗 فحص الروابط والـ IP",
        "tab_search": "🕵️‍♂️ البحث الجنائي الذكي",
        "tab_osint": "🌐 تتبع المعرفات (OSINT)",
        "tab_vault": "📁 إدارة قاعدة البيانات والأرشيف المركزي",
        "pdf_btn": "توليد التقرير الجنائي الرسمي (PDF)",
        "search_lbl": "اكتب الكلمة أو الرقم للبحث الفوري وإبراز السياق الجنائي:",
        "search_placeholder": "مثال: ابتزاز، تحويل، اختراق، blackmail, transfer",
        "vault_add_hdr": "إضافة مؤشر اشتباه جديد يدوياً إلى النظام",
        "vault_tbl_hdr": "أرشيف السجلات المركزي وقضايا الربط السابقة",
        "col_iban": "رقم الحساب البنكي (IBAN)",
        "col_status": "حالة المطابقة في القضايا الأخرى",
        "col_phone": "رقم الهاتف المرصود",
        "col_match": "المطابقة الجنائية",
        "col_email": "البريد الإلكتروني",
        "col_crypto": "عنوان محفظة التشفير",
        "col_url": "الرابط أو الـ IP المستخرج",
        "col_risk": "تقييم مستوى الخطورة",
        "col_score": "درجة التهديد الرقمي",
        "col_flags": "مؤشرات الشبهة المرصودة"
    }
}

# ==============================================================================
# 4. INTERFACE RENDERING
# ==============================================================================
st.set_page_config(page_title="CFIS - Advanced Forensic Suite", layout="wide")
apply_custom_theme()

lang = st.sidebar.selectbox("🌐 UI Language / لغة الواجهة", ["العربية", "English"])
tx = LEXICON[lang]

st.title(tx["title"])
st.subheader(tx["sub"])
st.markdown("<hr style='border-color: #30363d;'>", unsafe_allow_html=True)

st.sidebar.header(tx["sb_header"])

if 'loaded_chat' not in st.session_state:
    st.session_state['loaded_chat'] = None
if 'case_input' not in st.session_state:
    st.session_state['case_input'] = ""
if 'officer_input' not in st.session_state:
    st.session_state['officer_input'] = ""
if 'suspect_input' not in st.session_state:
    st.session_state['suspect_input'] = ""

case_id = st.sidebar.text_input(tx["sb_case"], value=st.session_state['case_input'], placeholder="2026/CID/1054")
investigator = st.sidebar.text_input(tx["sb_officer"], value=st.session_state['officer_input'], placeholder="Lt. Dana Khalifa")
suspect_name = st.sidebar.text_input(tx["sb_suspect"], value=st.session_state['suspect_input'], placeholder="Target_Alpha")

main_tabs = st.tabs(["🔍 " + ("Evidence Analyzer" if lang=="English" else "شاشة فحص وتحليل الأدلة"), "📁 " + tx["tab_vault"]])

with main_tabs[0]:
    uploaded_file = st.file_uploader(tx["upload_lbl"], type=["txt"])
    
    chat_data = None
    file_hash = "ARCHIVED_EVIDENCE_STREAM"
    
    if uploaded_file is not None:
        raw_bytes = uploaded_file.read()
        file_hash = calculate_sha256(raw_bytes)
        chat_data = raw_bytes.decode("utf-8")
        st.session_state['loaded_chat'] = chat_data
    elif st.session_state['loaded_chat'] is not None:
        chat_data = st.session_state['loaded_chat']

    if chat_data is not None:
        lines = chat_data.split('\n')
        
        # كرت الهش والتحكم بالأرشفة
        st.markdown(f"""
        <div class="forensic-card">
            <h4>📄 بصمة الدليل الرقمي (Integrity Validation)</h4>
            <code style="color: #58a6ff; font-size: 14px;">SHA-256: {file_hash}</code>
        </div>
        """, unsafe_allow_html=True)
        
        if case_id:
            if st.button("💾 " + ("Save Full Case File to Archive" if lang=="English" else "حفظ ملف القضية بالكامل في الأرشيف المركزي")):
                if save_full_case(case_id, investigator, suspect_name, file_hash, chat_data):
                    st.success("✅ " + ("Case file successfully securely archived inside CFIS Vault!" if lang=="English" else "تم حفظ وأرشفة ملف القضية بالكامل في قاعدة البيانات المحمية بنجاح!"))
                else:
                    st.error("Error archiving case file.")
        
        # --- ADVANCED ANALYTICS INTERFACES ---
        st.markdown("## 🧠 الاستخبارات النفسية والتحليل المتقدم للهوية")
        col_an1, col_an2, col_an3 = st.columns(3)
        
        with col_an1:
            st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
            st.markdown("#### 🎭 تحليل نبرة المحادثة والجريمة")
            tones = analyze_sentiment_and_tone(chat_data)
            fig_tone = px.bar(x=list(tones.values()), y=list(tones.keys()), orientation='h', labels={'x': 'Correlation (%)', 'y': 'Tone Classification'}, color=list(tones.values()), color_continuous_scale='Reds')
            fig_tone.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#c9d1d9")
            st.plotly_chart(fig_tone, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_an2:
            st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
            st.markdown("#### 💰 مصفوفة الحصر والابتزاز المالي")
            amts, total_money = extract_financial_amounts(chat_data)
            st.metric(label="Total Financial Extortion", value=f"{total_money} BHD")
            st.caption(f"Payment terms detected: {', '.join(amts) if amts else 'None'}")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_an3:
            st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
            st.markdown("#### 🕸️ هيكلة أطراف المحادثة والمهيمن")
            sender_pattern = r'-\s([^:]+):|\]\s([^:]+):'
            senders_raw = re.findall(sender_pattern, chat_data)
            senders = [s[0] if s[0] else s[1] for s in senders_raw if s[0] or s[1]]
            if senders:
                df_senders = pd.DataFrame(senders, columns=['Speaker']).value_counts().reset_index(name='Messages')
                fig_speaker = px.pie(df_senders, names='Speaker', values='Messages', color_discrete_sequence=px.colors.qualitative.Dark24)
                fig_speaker.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="#c9d1d9")
                st.plotly_chart(fig_speaker, use_container_width=True)
            else:
                st.info("No explicit structured participants found.")
            st.markdown("</div>", unsafe_allow_html=True)

        # --- ANOMALY DETECTIONS & ATTACHMENT TRIAGE ---
        col_an4, col_an5 = st.columns(2)
        with col_an4:
            st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
            st.markdown("#### ⚠️ فحص ثغرات الوقت والرسائل المحذوفة")
            omitted_images = chat_data.lower().count("image omitted") + chat_data.count("صورك")
            omitted_docs = chat_data.lower().count("document omitted") + chat_data.lower().count("ملف")
            st.write(f"📸 Media Exchanged / Flagged: **{omitted_images}**")
            st.write(f"📄 External Documents Logged: **{omitted_docs}**")
            st.markdown("</div>", unsafe_allow_html=True)
        with col_an5:
            st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
            overall_score, score_label = analyze_chat_threat_score(chat_data, lang)
            st.metric(label="Overall Conversation Threat Index", value=f"{overall_score}%")
            st.subheader(f"Triage Result: {score_label}")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<hr style='border-color: #30363d;'>", unsafe_allow_html=True)
        
        # Forensic Pattern Scanners (Regex)
        iban_pattern = r'[A-Z]{2}\d{2}[A-Z0-9]{10,30}'
        phone_pattern = r'\+?973\d{8}|\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        crypto_pattern = r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b|\bbc1[a-z0-9]{39,59}\b'

        extracted_ibans = list(set(re.findall(iban_pattern, chat_data)))
        extracted_emails = list(set(re.findall(email_pattern, chat_data)))
        extracted_crypto = list(set(re.findall(crypto_pattern, chat_data)))
        extracted_phones = list(set([p.strip() for p in re.findall(phone_pattern, chat_data) if len(p.strip()) > 7]))
        extracted_network = list(set(re.findall(url_pattern, chat_data) + re.findall(ip_pattern, chat_data)))

        timestamps = []
        time_pattern = r'(\d{2}/\d{2}/\d{4}),\s(\d{2}:\d{2}:\d{2})'
        for line in lines:
            match = re.search(time_pattern, line)
            if match:
                date_str, time_str = match.groups()
                try:
                    dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
                    timestamps.append({'DateTime': dt, 'Hour': dt.hour, 'Day': dt.strftime('%A')})
                except ValueError:
                    continue

        st.markdown(f"## {tx['charts_title']}")
        if timestamps:
            df_time = pd.DataFrame(timestamps)
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
                hour_counts = df_time['Hour'].value_counts().sort_index()
                fig_hour = px.bar(x=hour_counts.index, y=hour_counts.values, labels={'x': 'Hour', 'y': 'Count'}, title=tx["chart_h_title"], color_discrete_sequence=['#58a6ff'])
                fig_hour.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#c9d1d9")
                st.plotly_chart(fig_hour, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with col_c2:
                st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
                day_counts = df_time['Day'].value_counts()
                fig_day = px.pie(names=day_counts.index, values=day_counts.values, title=tx["chart_d_title"], color_discrete_sequence=px.colors.sequential.Blues_r)
                fig_day.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="#c9d1d9")
                st.plotly_chart(fig_day, use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(f"## {tx['art_title']}")
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([tx["tab_bank"], tx["tab_phone"], tx["tab_crypto"], tx["tab_url"], tx["tab_search"], tx["tab_osint"]])
        
        with tab1:
            if extracted_ibans:
                iban_records = []
                for iban in extracted_ibans:
                    m = check_cross_case(iban)
                    status = f"⚠️ MATCH: Case {m[0]} ({m[1]})" if m else ("Clear" if lang == "English" else "سجل نظيف")
                    iban_records.append({tx["col_iban"]: iban, tx["col_status"]: status})
                st.dataframe(pd.DataFrame(iban_records), use_container_width=True)
            else:
                st.write("No IBANs extracted.")
                
        with tab2:
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                if extracted_phones:
                    phone_records = []
                    for p in extracted_phones:
                        m = check_cross_case(p)
                        status = f"⚠️ MATCH: Case {m[0]}" if m else ("Clear" if lang == "English" else "سجل نظيف")
                        phone_records.append({tx["col_phone"]: p, tx["col_match"]: status})
                    st.dataframe(pd.DataFrame(phone_records), use_container_width=True)
                else:
                    st.write("No phone numbers extracted.")
            with col_p2:
                if extracted_emails:
                    email_records = []
                    for e in extracted_emails:
                        m = check_cross_case(e)
                        status = f"⚠️ MATCH: Case {m[0]}" if m else ("Clear" if lang == "English" else "سجل نظيف")
                        email_records.append({tx["col_email"]: e, tx["col_match"]: status})
                    st.dataframe(pd.DataFrame(email_records), use_container_width=True)
                else:
                    st.write("No email addresses extracted.")

        with tab3:
            if extracted_crypto:
                crypto_records = []
                for wallet in extracted_crypto:
                    m = check_cross_case(wallet)
                    status = f"⚠️ MATCH: Case {m[0]}" if m else ("Unlinked" if lang == "English" else "غير مرتبط بقضية")
                    crypto_records.append({tx["col_crypto"]: wallet, tx["col_match"]: status})
                st.dataframe(pd.DataFrame(crypto_records), use_container_width=True)
            else:
                st.write("No crypto wallets extracted.")

        with tab4:
            if extracted_network:
                net_records = []
                for item in extracted_network:
                    risk_label, risk_score, reason = analyze_url_or_ip(item, lang)
                    net_records.append({tx["col_url"]: item, tx["col_risk"]: risk_label, tx["col_score"]: risk_score, tx["col_flags"]: reason})
                st.dataframe(pd.DataFrame(net_records), use_container_width=True)
            else:
                st.write("No network indicators extracted.")

        with tab5:
            st.subheader(tx["tab_search"])
            # تم التحديث هنا لاستخدام الـ Placeholder الذكي والديناميكي المتغير حسب اللغة
            search_query = st.text_input(tx["search_lbl"], placeholder=tx["search_placeholder"])
            if search_query:
                search_results = []
                for idx, line in enumerate(lines):
                    if search_query.lower() in line.lower():
                        search_results.append({"Line #": idx + 1, "Content Match": line.strip()})
                if search_results:
                    st.warning(f"Found {len(search_results)} matching entries:")
                    st.dataframe(pd.DataFrame(search_results), use_container_width=True)

        with tab6:
            st.subheader("🌐 Meta & Social Media OSINT Footprint Scanner")
            target_username = st.text_input("Enter Suspect Username / Handle to Scan:", value=suspect_name if suspect_name else "", placeholder="e.g., target_alpha")
            
            if target_username:
                platforms = {
                    "Facebook (Meta Network)": f"https://www.facebook.com/{target_username}",
                    "Instagram (Meta Network)": f"https://www.instagram.com/{target_username}",
                    "X / Twitter": f"https://x.com/{target_username}",
                    "TikTok": f"https://www.tiktok.com/@{target_username}",
                    "GitHub Repository Link": f"https://github.com/{target_username}"
                }
                
                osint_data = []
                for plat, url in platforms.items():
                    osint_data.append({"Social Platform": plat, "Target Profile URL": url})
                
                st.dataframe(pd.DataFrame(osint_data), use_container_width=True)
                
                st.markdown("#### 🔗 Launch Quick Verification Profiles")
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                with col_btn1:
                    st.link_button("🌐 Open Facebook Profile", platforms["Facebook (Meta Network)"])
                with col_btn2:
                    st.link_button("📸 Open Instagram Profile", platforms["Instagram (Meta Network)"])
                with col_btn3:
                    st.link_button("🐦 Open X / Twitter", platforms["X / Twitter"])

        st.markdown("<hr style='border-color: #30363d;'>", unsafe_allow_html=True)
        if st.button(tx["pdf_btn"]):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", style="B", size=14)
            pdf.cell(200, 10, txt="KINGDOM OF BAHRAIN - MINISTRY OF INTERIOR", ln=1, align="C")
            pdf.set_font("Helvetica", size=10)
            pdf.cell(200, 6, txt="General Directorate of Anti-Corruption & Economic & Electronic Security", ln=1, align="C")
            pdf.cell(200, 6, txt="Anti-Electronic Crime Directorate / Digital Forensics Lab", ln=1, align="C")
            pdf.line(10, 36, 200, 36)
            pdf.ln(10)
            
            pdf.set_font("Helvetica", style="B", size=11)
            pdf.cell(200, 8, txt="I. FORENSIC INTELLIGENCE ASSESSMENT METADATA", ln=1)
            pdf.set_font("Helvetica", size=9)
            pdf.cell(200, 6, txt=f"Case File Reference ID: {case_id if case_id else 'FIELD TRIAGE RUN'}", ln=1)
            pdf.cell(200, 6, txt=f"Operating Field Officer: {investigator if investigator else 'CID FORENSIC INTERN'}", ln=1)
            pdf.cell(200, 6, txt=f"SHA-256 Checksum: {file_hash}", ln=1)
            pdf.cell(200, 6, txt=f"Dynamic Chat Threat Index: {overall_score}%", ln=1)
            pdf.cell(200, 6, txt=f"Financial Fraud Quantified: {total_money} BHD", ln=1)
            
            pdf_buffer = io.BytesIO()
            pdf_buffer.write(pdf.output())
            pdf_buffer.seek(0)
            st.download_button(label="⬇️ Download Official Triage Report (PDF)", data=pdf_buffer, file_name=f"Advanced_CFIS_Report.pdf", mime="application/pdf")

with main_tabs[1]:
    st.header(tx["tab_vault"])
    
    st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
    st.markdown("### 🔍 " + ("Retrieve Archived Full Case File" if lang=="English" else "استدعاء واسترجاع ملف قضية مؤرشف بالكامل"))
    search_case_id = st.text_input(("Enter Case Number to Load:" if lang=="English" else "أدخل رقم القضية المستهدفة للاستدعاء:"), placeholder="2026/CID/1054")
    
    if st.button(("Load & Analyze Case Archive" if lang=="English" else "تحميل وتحليل ملف القضية المسترجعة")):
        if search_case_id:
            case_data = load_full_case(search_case_id)
            if case_data:
                st.session_state['loaded_chat'] = case_data[0]
                st.session_state['case_input'] = search_case_id
                st.session_state['officer_input'] = case_data[1]
                st.session_state['suspect_input'] = case_data[2]
                st.success("✅ " + ("Case File retrieved successfully! Switch to 'Evidence Analyzer' tab to view analyses." if lang=="English" else "تم استدعاء ملف القضية بنجاح! انتقلي إلى تبويب 'شاشة فحص وتحليل الأدلة' لمشاهدة التحليلات فوراً."))
                st.rerun()
            else:
                st.error("❌ " + ("Case number not found in local database." if lang=="English" else "رقم القضية غير مسجل in أرشيف قاعدة البيانات."))
    st.markdown("</div>", unsafe_allow_html=True)
                
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_v1, col_v2 = st.columns([1, 2])
    with col_v1:
        st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
        st.subheader(tx["vault_add_hdr"])
        new_ind = st.text_input("Indicator Token (IBAN/Phone/IP):")
        new_type = st.selectbox("Type:", ["IBAN", "Phone", "Email", "Crypto", "IP Address"])
        new_case = st.text_input("Associated Case Number:")
        new_off = st.text_input("Logging Officer:")
        
        if st.button("Save New Threat Intel"):
            if new_ind and new_case and new_off:
                if add_manual_indicator(new_ind, new_type, new_case, new_off):
                    st.success("Indicator registered successfully!")
                else:
                    st.error("Error: Indicator already exists.")
        st.markdown("</div>", unsafe_allow_html=True)
                    
    with col_v2:
        st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
        st.subheader(tx["vault_tbl_hdr"])
        st.dataframe(get_all_indicators(), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

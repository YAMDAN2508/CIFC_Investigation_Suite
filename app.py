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

def calculate_sha256(bytes_data):
    return hashlib.sha256(bytes_data).hexdigest()

# ==============================================================================
# 2. THREAT INTEL & DYNAMIC SCORING ENGINE
# ==============================================================================
def analyze_chat_threat_score(text):
    high_risk_words = ['تهديد', 'ابتزاز', 'فلوس', 'حساب', 'تحويل', 'اخترقت', 'اطرش', 'money', 'blackmail', 'hack', 'transfer', 'wire']
    med_risk_words = ['رابط', 'يوزر', 'باسورد', 'ايميل', 'كود', 'link', 'password', 'code', 'verify', 'user']
    
    high_hits = sum(1 for w in high_risk_words if w in text.lower())
    med_hits = sum(1 for w in med_risk_words if w in text.lower())
    
    score = (high_hits * 15) + (med_hits * 7)
    score = min(score, 100)
    
    if score >= 60:
        return score, "CRITICAL RISK 🚨" if lang == "English" else "مستوى خطر حرج 🚨"
    elif score >= 25:
        return score, "MEDIUM RISK ⚠️" if lang == "English" else "مستوى خطر متوسط ⚠️"
    return score, "LOW RISK ✅" if lang == "English" else "مستوى خطر منخفض ✅"

def analyze_url_or_ip(item, lang):
    is_ip = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', item)
    if is_ip:
        return ("SUSPICIOUS IP 🌐" if lang == "English" else "IP مشبوه 🌐"), 70, ("Local Sandbox Routing Flagged" if lang == "English" else "تم رصد محاولة توجيه مشبوهة")
    
    suspicious_keywords = ['login', 'verify', 'update', 'bank', 'secure', 'free', 'gift', 'crypto', 'تحويل', 'تأمين']
    score = 0
    reasons = []
    for word in suspicious_keywords:
        if word in item.lower():
            score += 25
            reasons.append(f"Keyword '{word}'")
    if len(item) > 50:
        score += 20
        reasons.append("Long URL" if lang == "English" else "رابط طويل مريب")
    
    if score >= 50:
        return ("HIGH RISK 🚨" if lang == "English" else "خطورة عالية 🚨"), min(score, 100), ", ".join(reasons)
    elif score >= 25:
        return ("SUSPICIOUS ⚠️" if lang == "English" else "مشبوه ⚠️"), score, ", ".join(reasons)
    return ("SAFE ✅" if lang == "English" else "آمن ✅"), score, "-"

# ==============================================================================
# 3. BILINGUAL LEXICON
# ==============================================================================
LEXICON = {
    "English": {
        "title": "🛡️ Chat-Forensics Intelligence Suite (CFIS)",
        "sub": "CID Anti-Electronic Crime Directorate | Advanced Forensic Triage V2",
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
        "tab_vault": "📁 Case Vault Manager",
        "col_iban": "Extracted IBAN", "col_status": "Cross-Case Correlation Status",
        "col_phone": "Phone Number", "col_email": "Email Address", "col_match": "DB Match",
        "col_crypto": "Crypto Wallet Address", "col_url": "Extracted Target / IP",
        "col_risk": "Risk Categorization", "col_score": "Risk Score (%)", "col_flags": "Trigger Flags",
        "col_token": "Keyword Token", "col_hits": "Hits Discovered", "col_line": "Line #", "col_content": "Content Preview",
        "pdf_btn": "Generate Official PDF Forensics Report",
        "search_lbl": "Enter keyword or indicator to search in full conversation:",
        "vault_add_hdr": "Add New Forensic Indicator Manually",
        "vault_tbl_hdr": "Live Central Database Records Archive"
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
        "tab_vault": "📁 إدارة قاعدة البيانات (Vault)",
        "col_iban": "رقم الحساب المستخرج (IBAN)", "col_status": "حالة الربط والاشتباه عبر القضايا",
        "col_phone": "رقم الهاتف", "col_email": "البريد الإلكتروني", "col_match": "مطابقة قاعدة البيانات",
        "col_crypto": "عنوان محفظة العملات الرقمية", "col_url": "الرابط / الـ IP المستهدف",
        "col_risk": "تصنيف الخطورة", "col_score": "معدل الخطورة (%)", "col_flags": "مؤشرات الاشتباه",
        "col_token": "الكلمة المفتاحية", "col_hits": "عدد المرات المرصودة", "col_line": "رقم السطر", "col_content": "محتوى السطر داخل المحادثة",
        "pdf_btn": "توليد التقرير الجنائي الرسمي (PDF)",
        "search_lbl": "اكتب الكلمة أو الرقم للبحث الفوري وإبراز السياق الجنائي:",
        "vault_add_hdr": "إضافة مؤشر اشتباه جديد يدوياً إلى النظام",
        "vault_tbl_hdr": "أرشيف السجلات المركزي وقضايا الربط السابقة"
    }
}

# ==============================================================================
# 4. INTERFACE RENDERING
# ==============================================================================
st.set_page_config(page_title="CFIS - Advanced Forensic Suite", layout="wide")

lang = st.sidebar.selectbox("🌐 UI Language / لغة الواجهة", ["English", "العربية"])
tx = LEXICON[lang]

st.title(tx["title"])
st.subheader(tx["sub"])
st.markdown("---")

st.sidebar.header(tx["sb_header"])
case_id = st.sidebar.text_input(tx["sb_case"], placeholder="2026/CID/1054")
investigator = st.sidebar.text_input(tx["sb_officer"], placeholder="Lt. Dana Khalifa")
suspect_name = st.sidebar.text_input(tx["sb_suspect"], placeholder="Target_Alpha")

# Core Feature 1: Navigation Tabs to include Case Vault Manager
main_tabs = st.tabs(["🔍 " + ("Evidence Analyzer" if lang=="English" else "شاشة فحص وتحليل الأدلة"), "📁 " + tx["tab_vault"]])

with main_tabs[0]:
    uploaded_file = st.file_uploader(tx["upload_lbl"], type=["txt"])

    if uploaded_file is not None:
        st.info(tx["ingest"])
        
        raw_bytes = uploaded_file.read()
        file_hash = calculate_sha256(raw_bytes)
        chat_data = raw_bytes.decode("utf-8")
        lines = chat_data.split('\n')
        
        st.code(f"🔗 FORENSIC FILE SHA-256 HASH: {file_hash}", language="text")
        
        # Core Feature 2: Dynamic Chat Threat Assessment Score Card
        overall_score, score_label = analyze_chat_threat_score(chat_data)
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.metric(label="Overall Conversation Threat Index", value=f"{overall_score}%")
        with col_s2:
            st.subheader(f"Status Assessment: {score_label}")
            
        st.markdown("---")
        
        # Pattern Regex Engines
        iban_pattern = r'[A-Z]{2}\d{2}[A-Z0-9]{10,30}'
        phone_pattern = r'\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}'
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        crypto_pattern = r'\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b|\bbc1[a-z0-9]{39,59}\b'

        extracted_ibans = list(set(re.findall(iban_pattern, chat_data)))
        extracted_emails = list(set(re.findall(email_pattern, chat_data)))
        extracted_crypto = list(set(re.findall(crypto_pattern, chat_data)))
        extracted_phones = list(set([p.strip() for p in re.findall(phone_pattern, chat_data) if len(p.strip()) > 7]))
        
        # Combine URLs and IPs for the Threat Intel lookup
        extracted_network = list(set(re.findall(url_pattern, chat_data) + re.findall(ip_pattern, chat_data)))

        timestamps = []
        time_pattern = r'\[?(\d{2}/\d{2}/\d{4}),\s(\d{2}:\d{2}:\d{2})\]?'
        for line in lines:
            match = re.search(time_pattern, line)
            if match:
                date_str, time_str = match.groups()
                try:
                    dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
                    timestamps.append({'DateTime': dt, 'Hour': dt.hour, 'Day': dt.strftime('%A')})
                except ValueError:
                    continue

        st.success(tx["success"])
        
        # Visual Analytics
        st.markdown(f"## {tx['charts_title']}")
        if timestamps:
            df_time = pd.DataFrame(timestamps)
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                hour_counts = df_time['Hour'].value_counts().sort_index()
                fig_hour = px.bar(x=hour_counts.index, y=hour_counts.values, labels={'x': 'Hour', 'y': 'Count'}, title=tx["chart_h_title"], color_discrete_sequence=['#e74c3c'])
                st.plotly_chart(fig_hour, use_container_width=True)
            with col_c2:
                day_counts = df_time['Day'].value_counts()
                fig_day = px.pie(names=day_counts.index, values=day_counts.values, title=tx["chart_d_title"], color_discrete_sequence=px.colors.sequential.RdBu)
                st.plotly_chart(fig_day, use_container_width=True)

        st.markdown(f"## {tx['art_title']}")
        tab1, tab2, tab3, tab4, tab5 = st.tabs([tx["tab_bank"], tx["tab_phone"], tx["tab_crypto"], tx["tab_url"], tx["tab_search"]])
        
        with tab1:
            if extracted_ibans:
                iban_records = []
                for iban in extracted_ibans:
                    m = check_cross_case(iban)
                    status = f"⚠️ MATCH: Case {m[0]} ({m[1]})" if m else ("Clear" if lang == "English" else "سجل نظيف")
                    iban_records.append({tx["col_iban"]: iban, tx["col_status"]: status})
                st.dataframe(pd.DataFrame(iban_records), use_container_width=True)
                
        with tab2:
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                if extracted_phones:
                    phone_records = []
                    for p in extracted_phones:
                        m = check_cross_case(p)
                        status = f"⚠️ MATCH: Case {m[0]}" if m else "Clear"
                        phone_records.append({tx["col_phone"]: p, tx["col_match"]: status})
                    st.dataframe(pd.DataFrame(phone_records), use_container_width=True)
            with col_p2:
                if extracted_emails:
                    email_records = []
                    for e in extracted_emails:
                        m = check_cross_case(e)
                        status = f"⚠️ MATCH: Case {m[0]}" if m else "Clear"
                        email_records.append({tx["col_email"]: e, tx["col_match"]: status})
                    st.dataframe(pd.DataFrame(email_records), use_container_width=True)

        with tab3:
            if extracted_crypto:
                crypto_records = []
                for wallet in extracted_crypto:
                    m = check_cross_case(wallet)
                    status = f"⚠️ MATCH: Case {m[0]}" if m else "Unlinked"
                    crypto_records.append({tx["col_crypto"]: wallet, tx["col_match"]: status})
                st.dataframe(pd.DataFrame(crypto_records), use_container_width=True)

        with tab4:
            if extracted_network:
                net_records = []
                for item in extracted_network:
                    risk_label, risk_score, reason = analyze_url_or_ip(item, lang)
                    net_records.append({tx["col_url"]: item, tx["col_risk"]: risk_label, tx["col_score"]: risk_score, tx["col_flags"]: reason})
                st.dataframe(pd.DataFrame(net_records), use_container_width=True)

        # Core Feature 3: Advanced Contextual Highlight Search Bar
        with tab5:
            st.subheader(tx["tab_search"])
            search_query = st.text_input(tx["search_lbl"], placeholder="e.g., حساب bank, أو رقم محدد")
            if search_query:
                search_results = []
                for idx, line in enumerate(lines):
                    if search_query.lower() in line.lower():
                        search_results.append({"Line #": idx + 1, "Content Match": line.strip()})
                if search_results:
                    st.warning(f"Found {len(search_results)} matching entries:")
                    st.dataframe(pd.DataFrame(search_results), use_container_width=True)
                else:
                    st.info("No matches discovered for this query.")

        st.markdown("---")
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
            pdf.cell(200, 6, txt=f"Target Identifier Subject: {suspect_name if suspect_name else 'UNKNOWN TARGET'}", ln=1)
            pdf.cell(200, 6, txt=f"SHA-256 Verification Checksum: {file_hash}", ln=1)
            pdf.cell(200, 6, txt=f"Dynamic Chat Threat Index: {overall_score}% ({score_label})", ln=1)
            pdf.ln(6)
            
            pdf.set_font("Helvetica", style="B", size=11)
            pdf.cell(200, 8, txt="II. QUANTIFIED DISCOVERED EVIDENCE ARTIFACTS", ln=1)
            pdf.set_font("Helvetica", size=9)
            pdf.cell(200, 6, txt=f" -> Unique Financial Target IBAN Interceptions: {len(extracted_ibans)}", ln=1)
            pdf.cell(200, 6, txt=f" -> Unique Validated Communication Streams: {len(extracted_phones)}", ln=1)
            pdf.cell(200, 6, txt=f" -> Unique Crypto Asset Storage Nodes Found: {len(extracted_crypto)}", ln=1)
            pdf.cell(200, 6, txt=f" -> Extracted Network Identifiers (IP/URL): {len(extracted_network)}", ln=1)
            
            pdf_buffer = io.BytesIO()
            pdf_buffer.write(pdf.output())
            pdf_buffer.seek(0)
            
            st.download_button(label="⬇️ Download Official Triage Report (PDF)", data=pdf_buffer, file_name=f"Advanced_CFIS_Report.pdf", mime="application/pdf")

# Core Feature 4: Live Central Database Vault Manager Screen
with main_tabs[1]:
    st.header(tx["tab_vault"])
    
    col_v1, col_v2 = st.columns([1, 2])
    with col_v1:
        st.subheader(tx["vault_add_hdr"])
        new_ind = st.text_input("Indicator Token (IBAN/Phone/IP):")
        new_type = st.selectbox("Type:", ["IBAN", "Phone", "Email", "Crypto", "IP Address"])
        new_case = st.text_input("Associated Case Number:")
        new_off = st.text_input("Logging Officer:")
        
        if st.button("Save New Threat Intel"):
            if new_ind and new_case and new_off:
                success = add_manual_indicator(new_ind, new_type, new_case, new_off)
                if success:
                    st.success("Indicator registered into local intelligence successfully!")
                else:
                    st.error("Error: Indicator already exists in database.")
            else:
                st.warning("Please fill all metadata fields.")
                
    with col_v2:
        st.subheader(tx["vault_tbl_hdr"])
        db_df = get_all_indicators()
        st.dataframe(db_df, use_container_width=True)

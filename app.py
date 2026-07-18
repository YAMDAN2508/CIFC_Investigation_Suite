import streamlit as st
import pandas as pd
import plotly.express as px
import re
import sqlite3
import hashlib
from datetime import datetime
from fpdf import FPDF
import io
from deep_translator import GoogleTranslator

# ==============================================================================
# CSS CUSTOM STYLING (THEME & TYPOGRAPHY)
# ==============================================================================
def apply_custom_theme():
    st.markdown("""
        <style>
            .stApp {
                background-color: #0d1117;
                color: #c9d1d9;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            h1 {
                color: #58a6ff !important;
                font-weight: 700 !important;
                text-shadow: 0px 0px 10px rgba(88, 166, 255, 0.2);
            }
            h2, h3, h4 {
                color: #f0f6fc !important;
                font-weight: 600 !important;
            }
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
            .forensic-card {
                background-color: #161b22;
                border: 1px solid #30363d;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                margin-bottom: 15px;
            }
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
            section[data-testid="stSidebar"] {
                background-color: #090d13 !important;
                border-right: 1px solid #30363d;
            }
        </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# DATABASE SETUP & MANAGEMENT
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

def get_all_indicators():
    conn = sqlite3.connect('cfis_local_vault.db')
    df = pd.read_sql_query("SELECT * FROM historical_markers ORDER BY id DESC", conn)
    conn.close()
    return df

# ==============================================================================
# ADVANCED ANALYTICS ENGINES
# ==============================================================================
def analyze_chat_threat_score(text, lang_choice):
    high_risk_words = ['تهديد', 'ابتزاز', 'فلوس', 'حساب', 'تحويل', 'اخترقت', 'اطرش', 'صورك', 'fadiha', 'فضيحة', 'money', 'blackmail', 'hack', 'transfer', 'wire', 'scam', '凍結', '不正', '脅迫', '金']
    med_risk_words = ['رابط', 'يوزر', 'باسورد', 'ايميل', 'كود', 'واتساب', 'link', 'password', 'code', 'verify', 'user', 'whatsapp', 'リンク', '口座']
    
    high_hits = sum(1 for w in high_risk_words if w in text.lower())
    med_hits = sum(1 for w in med_risk_words if w in text.lower())
    
    score = (high_hits * 15) + (med_hits * 7)
    score = min(score, 100)
    
    if score >= 60:
        return score, "CRITICAL RISK 🚨" if lang_choice == "English" else "مستوى خطر حرج 🚨"
    elif score >= 25:
        return score, "MEDIUM RISK ⚠️" if lang_choice == "English" else "مستوى خطر متوسط ⚠️"
    return score, "LOW RISK ✅" if lang_choice == "English" else "مستوى خطر منخفض ✅"

def analyze_sentiment_and_tone(text):
    threat_words = ['تهديد', 'ابتزاز', 'فضيحة', 'بفضحك', 'انشر', 'صورك', 'blackmail', 'expose', 'threat', '不正', '脅迫', '拡散']
    fear_words = ['خايف', 'ارجوك', 'لا تنشر', 'ستر', 'تكفى', 'please', 'dont', 'afraid', 'stop', '不安', 'お願い', '助けて']
    financial_words = ['تحويل', 'فلوس', 'دينار', 'حساب', 'كاش', 'money', 'cash', 'pay', 'transfer', '振り込んで', 'デポジット', 'ディナール', '送金']
    
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
    amounts = re.findall(r'\b(\d+(?:\.\d+)?)\s*(?:دينار|بحريني|BD|BHD|dollar|\$|euro|日元|yen|ディナール)\b', text.lower())
    total_extracted = sum(float(amt) for amt in amounts)
    return amounts, total_extracted

def analyze_url_or_ip(item, lang_choice):
    is_ip = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', item)
    if is_ip:
        return ("SUSPICIOUS IP 🌐" if lang_choice == "English" else "IP مشبوه 🌐"), 70, "Flagged Infrastructure routing"
    suspicious_keywords = ['login', 'verify', 'update', 'bank', 'secure', 'free', 'gift', 'crypto', 'secure-bank']
    score = 0
    reasons = []
    for word in suspicious_keywords:
        if word in item.lower():
            score += 25
            reasons.append(f"Keyword '{word}'")
    if score >= 50:
        return ("HIGH RISK 🚨" if lang_choice == "English" else "خطورة عالية 🚨"), min(score, 100), ", ".join(reasons)
    return ("SAFE ✅" if lang_choice == "English" else "آمن ✅"), score, "-"

# ==============================================================================
# BILINGUAL LOCALIZATION LEXICON
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
        "save_vault_btn": "💾 Save Case to Central Archive",
        "intel_header": "🧠 Psychological Intelligence & Deep Identity Analysis",
        "card_tone": "🎭 Chat & Crime Tone Analysis",
        "card_financial": "💰 Financial Extortion Matrix",
        "card_speaker": "🕸️ Participant Structure & Dominance",
        "threat_idx": "💥 **Overall Threat Index:**",
        "forensic_triage_res": "| **Forensic Triage Result:**",
        "art_title": "🔍 High-Value Artifact Extraction & Threat Intel Matching",
        "tab_bank": "🏦 Banking Indicators",
        "tab_phone": "📞 Telephony & Comms",
        "tab_url": "🔗 URL & IP Scanner",
        "tab_vault": "📁 Case Vault & Archive Manager",
        "pdf_btn": "Generate Official PDF Forensics Report",
        "col_iban": "IBAN Account Number",
        "col_status": "Cross-Case Match Status",
        "col_phone": "Phone Number",
        "col_match": "Database Match",
        "col_email": "Email Address",
        "col_url": "Extracted URL / IP",
        "col_risk": "Risk Assessment",
        "col_score": "Threat Score",
        "col_flags": "Risk Indicators Found",
        "clear_btn": "🗑️ Clear Current Evidence",
        "checksum_lbl": "📄 Evidence Digital Fingerprint & Integrity Check",
        "trans_header": "🔠 Real-time Forensic Language Translator",
        "trans_lbl": "Select original chat file language (Source Language):",
        "trans_btn": "🔮 Translate & Update Forensic Matrix Now",
        "trans_back": "🔄 Revert to Original Untranslated File",
        "trans_matrix_lbl": "Current Translated Chat Stream:",
        "load_archive_btn": "Load Target Archive",
        "archive_search_lbl": "Recall previous case file by ID:",
        "stored_records_lbl": "🗄️ Currently Stored Central Records:",
        "no_evidence_msg": "⚠️ Please upload a chat file (.txt) first to begin the forensic evaluation.",
        "active_trans_msg": "📊 The forensic analytics matrix is currently operating on the [Approved Translated Text].",
        "no_participants": "No structured participants extracted."
    },
    "العربية": {
        "title": "🛡️ المنظومة الذكية لتحليل أدلة المحادثات الرقمية (CFIS)",
        "sub": "إدارة مكافحة الجرائم الإلكترونية | مختبر الأدلة الرقمية الجنائية",
        "sb_header": "📁 بيانات ملف القضية الجنائية",
        "sb_case": "رقم القضية الرسمي:",
        "sb_officer": "اسم ورتبة ضابط التحقيق:",
        "sb_suspect": "هوية / اسم الشهرة للمشتبه به:",
        "upload_lbl": "رفع سجلات المحادثات المصدرة (صيغة .txt)",
        "save_vault_btn": "💾 حفظ ملف القضية بالأرشيف المركزي",
        "intel_header": "🧠 الاستخبارات النفسية وتحليل الهوية المعمق",
        "card_tone": "🎭 تحليل نبرة المحادثة والجريمة",
        "card_financial": "💰 مصفوفة الحصر والابتزاز المالي",
        "card_speaker": "🕸️ هيكلة أطراف المحادثة والمهيمن",
        "threat_idx": "💥 **مؤشر خطورة المحادثة الكلي:**",
        "forensic_triage_res": "| **النتيجة الجنائية للفرز:**",
        "art_title": "🔍 استخراج الأدلة الرقمية ومطابقة الاستخبارات الجنائية",
        "tab_bank": "🏦 المؤشرات البنكية",
        "tab_phone": "📞 الاتصالات والهواتف",
        "tab_url": "🔗 فحص الروابط والـ IP",
        "tab_vault": "📁 إدارة قاعدة البيانات والأرشيف المركزي",
        "pdf_btn": "توليد التقرير الجنائي الرسمي (PDF)",
        "col_iban": "رقم الحساب البنكي (IBAN)",
        "col_status": "حالة المطابقة في القضايا الأخرى",
        "col_phone": "رقم الهاتف المرصود",
        "col_match": "المطابقة الجنائية",
        "col_email": "البريد الإلكتروني",
        "col_url": "الرابط أو الـ IP المستخرج",
        "col_risk": "تقييم مستوى الخطورة",
        "col_score": "درجة التهديد الرقمي",
        "col_flags": "مؤشارات الشبهة المرصودة",
        "clear_btn": "🗑️ مسح الملف الحالي",
        "checksum_lbl": "📄 بصمة الدليل الرقمي وضمان النزاهة",
        "trans_header": "🔠 كاشف ومترجم اللغات الجنائية الفوري",
        "trans_lbl": "اختر لغة ملف المحادثة الأصلي (Source Language):",
        "trans_btn": "🔮 ترجمة وتحديث مصفوفة التحليل الجنائي فوراً",
        "trans_back": "🔄 العودة للملف الأصلي (الغير مترجم)",
        "trans_matrix_lbl": "نص المحادثة المترجم الحالي:",
        "load_archive_btn": "تحميل الأرشيف المستهدف",
        "archive_search_lbl": "استدعاء قضية مؤرشفة سابقة برقم الملف:",
        "stored_records_lbl": "🗄️ السجلات المركزية المخزنة حالياً:",
        "no_evidence_msg": "⚠️ الرجاء رفع ملف المحادثة (.txt) أولاً للبدء بالفحص والتحليل الجنائي المتقدم.",
        "active_trans_msg": "📊 مصفوفة التحليل تعمل حالياً بناءً على [النص المترجم المعتمد].",
        "no_participants": "لم يتم استخراج أطراف مهيكلة للمحادثة."
    }
}

# ==============================================================================
# STATE INITIALIZATION & RENDER SYSTEM
# ==============================================================================
st.set_page_config(page_title="CFIS - Advanced Forensic Suite", layout="wide")
apply_custom_theme()

if 'active_chat_content' not in st.session_state:
    st.session_state['active_chat_content'] = None
if 'active_file_hash' not in st.session_state:
    st.session_state['active_file_hash'] = "NO_EVIDENCE_STREAM"
if 'translated_chat_content' not in st.session_state:
    st.session_state['translated_chat_content'] = None

lang = st.sidebar.selectbox("🌐 UI Language / لغة الواجهة", ["العربية", "English"])
tx = LEXICON[lang]

st.title(tx["title"])
st.subheader(tx["sub"])
st.markdown("<hr style='border-color: #30363d;'>", unsafe_allow_html=True)

st.sidebar.header(tx["sb_header"])
case_id = st.sidebar.text_input(tx["sb_case"], value="2026/CID/1054")
investigator = st.sidebar.text_input(tx["sb_officer"], value="Lt. Dana Khalifa")
suspect_name = st.sidebar.text_input(tx["sb_suspect"], value="Target_Alpha")

main_tabs = st.tabs(["🔍 Evidence Analyzer", "📁 " + tx["tab_vault"]])

with main_tabs[0]:
    uploaded_file = st.file_uploader(tx["upload_lbl"], type=["txt"])
    
    if uploaded_file is not None:
        try:
            file_bytes = uploaded_file.read()
            if len(file_bytes) > 0:
                st.session_state['active_chat_content'] = file_bytes.decode("utf-8")
                st.session_state['active_file_hash'] = hashlib.sha256(file_bytes).hexdigest()
                st.session_state['translated_chat_content'] = None
        except Exception as e:
            st.error(f"Error reading forensic stream: {e}")

    if st.session_state['translated_chat_content']:
        chat_data = st.session_state['translated_chat_content']
        st.info(tx["active_trans_msg"])
    else:
        chat_data = st.session_state['active_chat_content']

    if chat_data:
        # ----------------------------------------------------------------------
        # 🔮 كاشف ومترجم لغات الأدلة الجنائية
        # ----------------------------------------------------------------------
        st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
        st.markdown(f"### {tx['trans_header']}")
        src_lang = st.selectbox(tx["trans_lbl"], ["auto (كشف تلقائي)", "ja", "en", "ur", "hi", "ar"])
        target_lang_code = 'ar' if lang == "العربية" else 'en'
        
        if st.button(tx["trans_btn"]):
            with st.spinner("Translating..."):
                try:
                    raw_data = st.session_state['active_chat_content']
                    chunk_size = 2000
                    text_chunks = [raw_data[i:i+chunk_size] for i in range(0, len(raw_data), chunk_size)]
                    translated_chunks = []
                    for chunk in text_chunks:
                        if chunk.strip():
                            translated_text = GoogleTranslator(source=src_lang.split(" ")[0], target=target_lang_code).translate(chunk)
                            translated_chunks.append(translated_text)
                    
                    st.session_state['translated_chat_content'] = "".join(translated_chunks)
                    st.success("Success!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        
        if st.session_state['translated_chat_content']:
            st.text_area(tx["trans_matrix_lbl"], value=st.session_state['translated_chat_content'], height=150)
            if st.button(tx["trans_back"]):
                st.session_state['translated_chat_content'] = None
                st.rerun()
                
        st.markdown("</div>", unsafe_allow_html=True)

        # ----------------------------------------------------------------------
        # 📊 لوحات الإحصائيات الجنائية والتحليلات البيانية
        # ----------------------------------------------------------------------
        st.markdown(f"<div class='forensic-card'><h4>{tx['checksum_lbl']}</h4><code>SHA-256: {st.session_state['active_file_hash']}</code></div>", unsafe_allow_html=True)
        
        if st.button(tx["clear_btn"]):
            st.session_state['active_chat_content'] = None
            st.session_state['translated_chat_content'] = None
            st.session_state['active_file_hash'] = "NO_EVIDENCE_STREAM"
            st.rerun()

        if st.button(tx["save_vault_btn"]):
            save_full_case(case_id, investigator, suspect_name, st.session_state['active_file_hash'], chat_data)
            st.success("Saved!")

        st.markdown(f"## {tx['intel_header']}")
        col_an1, col_an2, col_an3 = st.columns(3)
        
        with col_an1:
            st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
            st.markdown(f"#### {tx['card_tone']}")
            tones = analyze_sentiment_and_tone(chat_data)
            fig_tone = px.bar(x=list(tones.values()), y=list(tones.keys()), orientation='h', color=list(tones.values()), color_continuous_scale='Reds')
            fig_tone.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#c9d1d9")
            st.plotly_chart(fig_tone, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_an2:
            st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
            st.markdown(f"#### {tx['card_financial']}")
            amts, total_money = extract_financial_amounts(chat_data)
            st.metric(label="Total Financial Extortion Detected", value=f"{total_money} BHD / Units")
            st.caption(f"Detected Terms: {', '.join(amts) if amts else 'None'}")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col_an3:
            st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
            st.markdown(f"#### {tx['card_speaker']}")
            sender_pattern = r'-\s([^:]+):|\]\s([^:]+):|\[[^\]]+\]\s([^:]+):'
            senders_raw = re.findall(sender_pattern, chat_data)
            senders = [s[0] if s[0] else (s[1] if s[1] else s[2]) for s in senders_raw if any(s)]
            if senders:
                df_senders = pd.DataFrame(senders, columns=['Speaker']).value_counts().reset_index(name='Messages')
                fig_speaker = px.pie(df_senders, names='Speaker', values='Messages', color_discrete_sequence=px.colors.qualitative.Dark24)
                fig_speaker.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="#c9d1d9")
                st.plotly_chart(fig_speaker, use_container_width=True)
            else:
                st.info(tx["no_participants"])
            st.markdown("</div>", unsafe_allow_html=True)

        overall_score, score_label = analyze_chat_threat_score(chat_data, lang)
        st.markdown(f"<div class='forensic-card'>{tx['threat_idx']} {overall_score}% {tx['forensic_triage_res']} {score_label}</div>", unsafe_allow_html=True)

        # ----------------------------------------------------------------------
        # 🕵️‍♂️ استخراج الأدلة الرقمية ومطابقة الاستخبارات
        # ----------------------------------------------------------------------
        iban_pattern = r'[A-Z]{2}\d{2}[A-Z0-9]{10,30}'
        phone_pattern = r'\+?973\d{8}'
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        btc_pattern = r'\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b'

        extracted_ibans = list(set(re.findall(iban_pattern, chat_data)))
        extracted_emails = list(set(re.findall(email_pattern, chat_data)))
        extracted_phones = list(set([p.strip() for p in re.findall(phone_pattern, chat_data) if len(p.strip()) > 7]))
        extracted_network = list(set(re.findall(url_pattern, chat_data) + re.findall(ip_pattern, chat_data)))
        extracted_btc = list(set(re.findall(btc_pattern, chat_data)))

        st.markdown(f"## {tx['art_title']}")
        tab1, tab2, tab3 = st.tabs([tx["tab_bank"], tx["tab_phone"], tx["tab_url"]])
        
        with tab1:
            if extracted_ibans or extracted_btc:
                if extracted_ibans:
                    st.write("🏦 Extracted IBANs:")
                    iban_records = [{tx["col_iban"]: iban, tx["col_status"]: ("⚠️ MATCH FOUND" if check_cross_case(iban) else "Clear")} for iban in extracted_ibans]
                    st.dataframe(pd.DataFrame(iban_records), use_container_width=True)
                if extracted_btc:
                    st.write("🪙 Extracted Crypto Wallets:")
                    st.dataframe(pd.DataFrame(extracted_btc, columns=["Crypto Address"]), use_container_width=True)
            else:
                st.info("No banking/crypto artifacts extracted.")
                
        with tab2:
            if extracted_phones or extracted_emails:
                st.write("Phones Captured:", extracted_phones)
                st.write("Emails Captured:", extracted_emails)
            else:
                st.info("No telephony or email communication signatures detected.")

        with tab3:
            if extracted_network:
                net_records = []
                for item in extracted_network:
                    risk_label, risk_score, reason = analyze_url_or_ip(item, lang)
                    net_records.append({tx["col_url"]: item, tx["col_risk"]: risk_label, tx["col_score"]: risk_score, tx["col_flags"]: reason})
                st.dataframe(pd.DataFrame(net_records), use_container_width=True)
            else:
                st.info("No network infrastructure indicators detected.")

        if st.button(tx["pdf_btn"]):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", style="B", size=14)
            pdf.cell(200, 10, txt="MINISTRY OF INTERIOR - CRIMINAL INVESTIGATION LAB", ln=1, align="C")
            pdf_bytes = pdf.output()
            if isinstance(pdf_bytes, str): pdf_bytes = pdf_bytes.encode('latin1')
            st.download_button(label="⬇️ Download PDF Report", data=io.BytesIO(pdf_bytes), file_name=f"CFIS_Report_{case_id.replace('/', '_')}.pdf", mime="application/pdf")
    else:
        st.info(tx["no_evidence_msg"])

with main_tabs[1]:
    st.header(tx["tab_vault"])
    search_case_id = st.text_input(tx["archive_search_lbl"])
    if st.button(tx["load_archive_btn"]):
        res = load_full_case(search_case_id)
        if res:
            st.session_state['active_chat_content'] = res[0]
            st.session_state['active_file_hash'] = res[3]
            st.session_state['translated_chat_content'] = None
            st.success("Loaded!")
            st.rerun()
            
    st.markdown(f"### {tx['stored_records_lbl']}")
    st.dataframe(get_all_indicators(), use_container_width=True)

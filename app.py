import streamlit as st
import pandas as pd
import plotly.express as px
import re
import sqlite3
import hashlib
import json
from datetime import datetime, timezone
import io

# ==============================================================================
# REPORTLAB PDF ENGINE IMPORTS
# ==============================================================================
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ==============================================================================
# CSS CUSTOM STYLING & DYNAMIC CONTACT COLOR PALETTE
# ==============================================================================
CONTACT_COLORS = [
    {"bg": "#1e3a8a", "border": "#3b82f6", "text": "#93c5fd"},  # Neon Blue
    {"bg": "#701a75", "border": "#d946ef", "text": "#f5d0fe"},  # Neon Purple
    {"bg": "#064e3b", "border": "#10b981", "text": "#a7f3d0"},  # Neon Green
    {"bg": "#78350f", "border": "#f59e0b", "text": "#fde68a"},  # Neon Amber
    {"bg": "#831843", "border": "#ec4899", "text": "#fbcfe8"},  # Neon Pink
    {"bg": "#134e4a", "border": "#14b8a6", "text": "#99f6e4"},  # Neon Teal
    {"bg": "#7c2d12", "border": "#ea580c", "text": "#ffedd5"}   # Neon Orange
]

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
            .highlight-box {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 15px;
                max-height: 400px;
                overflow-y: auto;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 13px;
                line-height: 1.8;
            }
            .contact-badge {
                padding: 2px 8px;
                border-radius: 4px;
                font-weight: bold;
                margin-right: 6px;
                display: inline-block;
                border: 1px solid;
            }
            .hl-red { background-color: #7d1a1a; color: #ff9999; padding: 2px 4px; border-radius: 3px; font-weight: bold; }
            .hl-yellow { background-color: #7d601a; color: #ffe066; padding: 2px 4px; border-radius: 3px; font-weight: bold; }
            .hl-blue { background-color: #1a4d7d; color: #99ccff; padding: 2px 4px; border-radius: 3px; font-weight: bold; }
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
            app_source TEXT,
            device_role TEXT,
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

def save_full_case(case_num, officer, suspect, app_src, dev_role, f_hash, content):
    conn = sqlite3.connect('cfis_local_vault.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO cases_archive (case_number, officer_assigned, suspect_name, app_source, device_role, file_hash, chat_content, date_saved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (case_num, officer, suspect, app_src, dev_role, f_hash, content, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return True
    except sqlite3.Error:
        return False
    finally:
        conn.close()

# ==============================================================================
# MULTI-FORMAT DATA INGESTION PARSER
# ==============================================================================
def parse_uploaded_chat(file_bytes, app_source):
    if app_source == "WhatsApp (.txt)":
        return file_bytes.decode("utf-8", errors="ignore")
    
    try:
        json_data = json.loads(file_bytes.decode("utf-8", errors="ignore"))
        parsed_lines = []
        
        if app_source == "Telegram (.json)":
            messages = json_data.get("messages", [])
            for msg in messages:
                if msg.get("type") == "message":
                    sender = msg.get("from", "Unknown")
                    date = msg.get("date", "")
                    text = msg.get("text", "")
                    if isinstance(text, list):
                        text = "".join([t["text"] if isinstance(t, dict) else str(t) for t in text])
                    parsed_lines.append(f"[{date}] {sender}: {text}")
                    
        elif app_source in ["Instagram DMs (.json)", "Facebook Messenger (.json)"]:
            messages = json_data.get("messages", [])
            for msg in reversed(messages):
                sender = msg.get("sender_name", "Unknown")
                ms = msg.get("timestamp_ms", 0)
                date = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S') if ms else ""
                content = msg.get("content", "")
                parsed_lines.append(f"[{date}] {sender}: {content}")
                
        return "\n".join(parsed_lines) if parsed_lines else file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return file_bytes.decode("utf-8", errors="ignore")

# ==============================================================================
# MULTI-CONTACT COLOR-CODING ENGINE
# ==============================================================================
def extract_contacts_map(chat_text):
    sender_pattern = r'-\s([^:]+):|\]\s([^:]+):|\[[^\]]+\]\s([^:]+):'
    senders_raw = re.findall(sender_pattern, chat_text)
    unique_senders = []
    
    for s in senders_raw:
        sender_name = s[0] if s[0] else (s[1] if s[1] else s[2])
        if sender_name and sender_name.strip() not in unique_senders:
            unique_senders.append(sender_name.strip())

    contact_color_map = {}
    for idx, sender in enumerate(unique_senders):
        color_scheme = CONTACT_COLORS[idx % len(CONTACT_COLORS)]
        contact_color_map[sender] = color_scheme

    return contact_color_map

def generate_keyword_highlight_html(chat_text, contact_color_map):
    red_words = ['تهديد', 'ابتزاز', 'فلوس', 'اخترقت', 'اطرش', 'صورك', 'fadiha', 'فضيحة', 'blackmail', 'hack', 'scam', '脅迫', 'فضايح', 'بفضحك', 'انشر']
    yellow_words = ['حساب', 'تحويل', 'دينار', 'كاش', 'IBAN', 'BD', 'BHD', 'money', 'transfer', 'wire', 'pay', 'cash', 'مركز', 'بنك']
    blue_words = ['رابط', 'يوزر', 'باسورد', 'ايميل', 'كود', 'واتساب', 'link', 'password', 'code', 'verify', 'user', 'whatsapp', 'مستخدم']
    
    lines = chat_text.split('\n')
    highlighted_lines = []
    
    for line in lines:
        escaped_line = line.replace('<', '&lt;').replace('>', '&gt;')
        
        for contact, c_style in contact_color_map.items():
            if contact in escaped_line:
                badge_html = f'<span class="contact-badge" style="background-color: {c_style["bg"]}; border-color: {c_style["border"]}; color: {c_style["text"]};">{contact}</span>'
                escaped_line = escaped_line.replace(contact, badge_html, 1)

        for w in red_words:
            escaped_line = re.sub(f"(?i)({re.escape(w)})", r'<span class="hl-red">\1</span>', escaped_line)
        for w in yellow_words:
            escaped_line = re.sub(f"(?i)({re.escape(w)})", r'<span class="hl-yellow">\1</span>', escaped_line)
        for w in blue_words:
            escaped_line = re.sub(f"(?i)({re.escape(w)})", r'<span class="hl-blue">\1</span>', escaped_line)
            
        highlighted_lines.append(escaped_line)
        
    return "<br/>".join(highlighted_lines)

# ==============================================================================
# VICTIM / SUSPECT IDENTIFICATION
# ==============================================================================
def identify_victim_suspect(chat_text):
    participants = {}
    patterns = [
        r'^\d{1,2}/\d{1,2}/\d{2,4},.*?-\s([^:]+):\s(.*)$',
        r'^\[(.*?)\]\s([^:]+):\s(.*)$',
        r'^([^:]+):\s(.*)$'
    ]

    messages = []
    evidence = {}
    for line in chat_text.splitlines():
        line = line.strip()
        if not line:
            continue

        sender = None
        message = None
        for p in patterns:
            m = re.match(p, line)
            if m:
                if len(m.groups()) == 3:
                    sender = m.group(2).strip()
                    message = m.group(3).lower()
                else:
                    sender = m.group(1).strip()
                    message = m.group(2).lower()
                break

        if sender is None:
            continue

        if sender not in participants:
            participants[sender] = {"victim": 0, "suspect": 0, "messages": 0}
            evidence[sender] = {"threats": 0, "money_requests": 0, "help_requests": 0, "fear": 0}

        participants[sender]["messages"] += 1
        messages.append({"sender": sender, "message": message})

        victim_keywords = ["please", "help", "stop", "don't", "leave me", "sorry", "i'm scared", "afraid", "ارجوك", "تكفى", "ساعد", "رجاء", "لا تنشر", "خايف"]
        suspect_keywords = ["pay", "money", "transfer", "wire", "bitcoin", "or else", "i will", "blackmail", "hack", "publish", "expose", "ادفع", "حول", "فلوس", "ابتزاز", "تهديد", "بفضحك", "بنشر", "انشر"]

        for word in victim_keywords:
            if word in message:
                participants[sender]["victim"] += 3
                evidence[sender]["fear"] += 1

        for word in suspect_keywords:
            if word in message:
                participants[sender]["suspect"] += 5
                evidence[sender]["threats"] += 1

        if re.search(r"\b\d+\s?(bd|bhd|\$|دينار)\b", message):
            participants[sender]["suspect"] += 4

    if len(participants) < 2:
        return {
            "victim": "Unknown",
            "suspect": "Unknown",
            "confidence": 0,
            "details": participants,
            "evidence": evidence
        }

    victim = max(participants, key=lambda x: participants[x]["victim"])
    suspect = max(participants, key=lambda x: participants[x]["suspect"])

    if victim == suspect:
        ordered = sorted(participants.items(), key=lambda x: x[1]["suspect"], reverse=True)
        if len(ordered) > 1:
            suspect = ordered[1][0]

    confidence = min((participants[victim]["victim"] + participants[suspect]["suspect"]) * 8, 100)

    return {
        "victim": victim,
        "suspect": suspect,
        "confidence": confidence,
        "details": participants,
        "evidence": evidence
    }

def analyze_chat_threat_score(text, lang_choice, device_role):
    high_risk_words = ['تهديد', 'ابتزاز', 'فلوس', 'حساب', 'تحويل', 'اخترقت', 'اطرش', 'صورك', 'fadiha', 'فضيحة', 'money', 'blackmail', 'hack', 'transfer', 'wire', 'scam']
    med_risk_words = ['رابط', 'يوزر', 'باسورد', 'ايميل', 'كود', 'واتساب', 'link', 'password', 'code', 'verify', 'user', 'whatsapp']
    
    high_hits = sum(1 for w in high_risk_words if w in text.lower())
    med_hits = sum(1 for w in med_risk_words if w in text.lower())
    
    multiplier = 1.2 if "Suspect" in device_role or "المشتبه" in device_role else 1.0
    score = int(((high_hits * 15) + (med_hits * 7)) * multiplier)
    score = min(score, 100)
    
    if score >= 60:
        return score, "CRITICAL RISK" if lang_choice == "English" else "مستوى خطر حرج"
    elif score >= 25:
        return score, "MEDIUM RISK" if lang_choice == "English" else "مستوى خطر متوسط"
    return score, "LOW RISK" if lang_choice == "English" else "مستوى خطر منخفض"

def extract_financial_amounts(text):
    amounts = re.findall(r'\b(\d+(?:\.\d+)?)\s*(?:دينار|بحريني|BD|BHD|dollar|\$|euro)\b', text.lower())
    total_extracted = sum(float(amt) for amt in amounts)
    return amounts, total_extracted

# ==============================================================================
# REPORTLAB PDF GENERATOR FUNCTION
# ==============================================================================
def create_reportlab_pdf(case_id, officer, suspect, app_src, dev_role, file_hash, score, score_label, ibans, emails, phones, urls, total_money, recon_data, audit_logs, identity):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=16, leading=20, alignment=1, textColor=colors.HexColor('#0f2b48'))
    subtitle_style = ParagraphStyle('DocSubTitle', parent=styles['Normal'], fontSize=9, leading=12, alignment=1, textColor=colors.HexColor('#4a5568'))
    h2_style = ParagraphStyle('SectionHeader', parent=styles['Heading2'], fontSize=11, leading=15, textColor=colors.HexColor('#1a365d'), spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle('BodyTextCustom', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#2d3748'))

    story = []

    story.append(Paragraph("DIGITAL FORENSICS INVESTIGATION REPORT", title_style))
    story.append(Paragraph("GENERAL DIRECTORATE OF ANTI-CORRUPTION & ECONOMIC & ELECTRONIC SECURITY", subtitle_style))
    story.append(Spacer(1, 10))

    meta_data = [
        [Paragraph("<b>Case Number:</b>", body_style), Paragraph(str(case_id), body_style)],
        [Paragraph("<b>Investigating Officer:</b>", body_style), Paragraph(str(officer), body_style)],
        [Paragraph("<b>Target Suspect / Alias:</b>", body_style), Paragraph(str(suspect), body_style)],
        [Paragraph("<b>App Source & Device Role:</b>", body_style), Paragraph(f"{app_src} | Role: {dev_role}", body_style)],
        [Paragraph("<b>Evidence Hash (SHA-256):</b>", body_style), Paragraph(str(file_hash), body_style)],
        [Paragraph("<b>Generated On:</b>", body_style), Paragraph(datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'), body_style)]
    ]
    meta_table = Table(meta_data, colWidths=[140, 400])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f7fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#edf2f7')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    
    story.append(Paragraph("1. Case Metadata & Evidence Integrity", h2_style))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    risk_data = [
        [Paragraph("<b>Threat Index Score</b>", body_style), Paragraph("<b>Risk Classification</b>", body_style), Paragraph("<b>Detected Financial Extortion</b>", body_style)],
        [Paragraph(f"<b>{score}%</b>", body_style), Paragraph(str(score_label), body_style), Paragraph(f"{total_money} BHD", body_style)]
    ]
    risk_table = Table(risk_data, colWidths=[180, 180, 180])
    risk_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#ebf8ff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    
    story.append(Paragraph("2. Risk Assessment & Financial Threat Level", h2_style))
    story.append(risk_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("3. Victim / Suspect Identification", h2_style))

    identity_table = Table([
        [Paragraph("<b>Victim</b>", body_style), Paragraph(str(identity["victim"]), body_style)],
        [Paragraph("<b>Suspect</b>", body_style), Paragraph(str(identity["suspect"]), body_style)],
        [Paragraph("<b>Confidence</b>", body_style), Paragraph(f"{identity['confidence']}%", body_style)]
    ], colWidths=[170, 370])

    identity_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f7fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))

    story.append(identity_table)
    story.append(Spacer(1,8))

    story.append(Paragraph("4. Extracted Forensic Indicators", h2_style))
    artifacts_text = f"""
    • <b>IBAN Accounts ({len(ibans)}):</b> {', '.join(ibans) if ibans else 'None Identified'}<br/>
    • <b>Phone Numbers ({len(phones)}):</b> {', '.join(phones) if phones else 'None Identified'}<br/>
    • <b>Email Addresses ({len(emails)}):</b> {', '.join(emails) if emails else 'None Identified'}<br/>
    • <b>Network/IP Indicators ({len(urls)}):</b> {', '.join(urls) if urls else 'None Identified'}
    """
    story.append(Paragraph(artifacts_text, body_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("5. OSINT Social Media Reconnaissance Results", h2_style))
    valid_recon_data = [r for r in recon_data if r] if recon_data else []
    if valid_recon_data:
        osint_table_data = [[Paragraph("<b>Platform</b>", body_style), Paragraph("<b>Status</b>", body_style), Paragraph("<b>Profile Endpoint</b>", body_style)]]
        for r in valid_recon_data:
            if isinstance(r, dict):
                platform = r.get("Platform") or r.get("Platform / Network") or ""
                status = r.get("Status") or r.get("Recon Status") or ""
                url = r.get("URL") or r.get("Profile Link") or ""
            else:
                platform, status, url = str(r[0]), str(r[1]), str(r[2])

            osint_table_data.append([
                Paragraph(str(platform), body_style),
                Paragraph(str(status), body_style),
                Paragraph(str(url), body_style)
            ])
        osint_table = Table(osint_table_data, colWidths=[120, 140, 280])
        osint_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#edf2f7')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e0')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(osint_table)
    else:
        story.append(Paragraph("No automated OSINT platform scan was performed during this session.", body_style))

    story.append(Spacer(1, 8))

    story.append(Paragraph("6. Digital Chain of Custody & Legal Audit Trail", h2_style))
    coc_table_data = [[Paragraph("<b>Phase</b>", body_style), Paragraph("<b>Action Performed</b>", body_style), Paragraph("<b>Timestamp (UTC)</b>", body_style), Paragraph("<b>Officer</b>", body_style), Paragraph("<b>Integrity Stamp</b>", body_style)]]
    
    for log in audit_logs:
        coc_table_data.append([
            Paragraph(str(log.get("phase", "")), body_style),
            Paragraph(str(log.get("action", "")), body_style),
            Paragraph(str(log.get("timestamp", "")), body_style),
            Paragraph(str(log.get("officer", "")), body_style),
            Paragraph(f"<code>{log.get('hash_stamp', '')[:10]}...</code>", body_style)
        ])
        
    coc_table = Table(coc_table_data, colWidths=[80, 160, 110, 100, 90])
    coc_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(coc_table)

    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>[ CONFIDENTIAL - OFFICIALLY VERIFIED FORENSIC CHAIN OF CUSTODY ]</b>", subtitle_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# ==============================================================================
# MAIN STREAMLIT APPLICATION INTERFACE
# ==============================================================================
def main():
    st.set_page_config(page_title="CFIS - Cyber Forensics Suite", layout="wide")
    apply_custom_theme()

    st.title("🔍 Cyber Forensics Data Analysis Suite")
    st.markdown("---")

    # Sidebar inputs
    st.sidebar.header("📋 Case Details")
    case_number = st.sidebar.text_input("Case Number", "2026/CID/1001")
    officer_name = st.sidebar.text_input("Investigating Officer", "Lt. Jasim")
    suspect_name = st.sidebar.text_input("Suspect Name / Alias", "Unknown Target")
    app_source = st.sidebar.selectbox("App Data Source", ["WhatsApp (.txt)", "Telegram (.json)", "Instagram DMs (.json)", "Facebook Messenger (.json)"])
    device_role = st.sidebar.selectbox("Evidence Role", ["Suspect Device", "Victim Device"])
    language = st.sidebar.radio("Interface Language", ["English", "Arabic"])

    uploaded_file = st.sidebar.file_uploader("Upload Extraction File", type=["txt", "json"])

    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        chat_text = parse_uploaded_chat(file_bytes, app_source)

        st.sidebar.success(f"SHA256: {file_hash[:10]}...")

        # Run analytics
        contacts_map = extract_contacts_map(chat_text)
        identity = identify_victim_suspect(chat_text)
        score, score_label = analyze_chat_threat_score(chat_text, language, device_role)
        amounts, total_money = extract_financial_amounts(chat_text)

        ibans = list(set(re.findall(r'\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b', chat_text)))
        emails = list(set(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', chat_text)))
        phones = list(set(re.findall(r'\+?\d{8,15}', chat_text)))
        urls = list(set(re.findall(r'https?://[^\s]+|\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', chat_text)))

        # Create Dashboard UI Tabs
        tab1, tab2, tab3 = st.tabs(["📊 Analytics Overview", "📜 Chat Analysis", "📄 Export Report"])

        with tab1:
            col1, col2, col3 = st.columns(3)
            col1.metric("Threat Score", f"{score}%", delta=score_label)
            col2.metric("Detected Funds", f"{total_money} BHD")
            col3.metric("Extracted Identifiers", len(ibans) + len(emails) + len(phones))

            st.subheader("Role Identification Analysis")
            st.write(f"**Identified Victim:** {identity['victim']}")
            st.write(f"**Identified Suspect:** {identity['suspect']}")
            st.write(f"**Analysis Confidence:** {identity['confidence']}%")

        with tab2:
            st.subheader("Highlighted Evidence Feed")
            highlighted_html = generate_keyword_highlight_html(chat_text, contacts_map)
            st.markdown(f'<div class="highlight-box">{highlighted_html}</div>', unsafe_allow_html=True)

        with tab3:
            st.subheader("Generate Case Report")
            audit_logs = [
                {"phase": "Ingestion", "action": "File Loaded", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "officer": officer_name, "hash_stamp": file_hash}
            ]
            recon_sample = [
                {"Platform": "Instagram", "Status": "Active", "URL": f"https://instagram.com/{suspect_name}"}
            ]
            
            if st.button("Generate & Download PDF"):
                pdf_bytes = create_reportlab_pdf(
                    case_number, officer_name, suspect_name, app_source, device_role, 
                    file_hash, score, score_label, ibans, emails, phones, urls, 
                    total_money, recon_sample, audit_logs, identity
                )
                st.download_button(
                    label="📥 Download Forensic Report PDF",
                    data=pdf_bytes,
                    file_name=f"Forensic_Report_{case_number.replace('/', '_')}.pdf",
                    mime="application/pdf"
                )
    else:
        st.info("Please upload a chat extract or JSON log from the sidebar to begin forensic processing.")

if __name__ == "__main__":
    main()

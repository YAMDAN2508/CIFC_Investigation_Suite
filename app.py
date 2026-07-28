import streamlit as st
import pandas as pd
import plotly.express as px
import re
import sqlite3
import hashlib
import json
from datetime import datetime, timezone
import io
import requests
from deep_translator import GoogleTranslator

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

def load_full_case(case_num):
    conn = sqlite3.connect('cfis_local_vault.db')
    cursor = conn.cursor()
    cursor.execute("SELECT chat_content, officer_assigned, suspect_name, file_hash, app_source, device_role FROM cases_archive WHERE case_number = ?", (case_num,))
    result = cursor.fetchone()
    conn.close()
    return result

def get_all_indicators():
    conn = sqlite3.connect('cfis_local_vault.db')
    df = pd.read_sql_query("SELECT * FROM historical_markers ORDER BY id DESC", conn)
    conn.close()
    return df

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
# MULTI-CONTACT COLOR-CODING ENGINE & ARTIFACT LEGEND
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

def render_artifact_legend_with_roles(suspect_name, device_role, victim_name="Victim / Complainant"):
    """Renders the Artifact Legend with Victim and Suspect identities directly beneath it."""
    is_suspect_device = "Suspect" in device_role or "المشتبه" in device_role
    device_owner_label = "Suspect Device (المشتبه به)" if is_suspect_device else "Victim Device (الضحية)"
    
    st.markdown(f"""
        <div style="background-color: #161b22; border: 1px solid #30363d; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px;">
            <div style="font-size: 13px; font-weight: bold; color: #8b949e; margin-bottom: 6px;">
                🏷️ Artifact Legend: 
                <span class="hl-red">Threat / Extortion</span> | 
                <span class="hl-yellow">Financial / IBAN</span> | 
                <span class="hl-blue">Credentials / URL</span>
            </div>
            <hr style="border-top: 1px solid #30363d; margin: 8px 0;" />
            <div style="display: flex; gap: 20px; font-size: 13px; font-weight: 600; align-items: center; flex-wrap: wrap;">
                <div>
                    🔴 <span style="color: #f85149;">Suspect (المشتبه به):</span> 
                    <span style="color: #f0f6fc; background-color: #21262d; padding: 2px 8px; border-radius: 4px; border: 1px solid #da3633;">
                        {suspect_name if suspect_name else "Unassigned / Target Alpha"}
                    </span>
                </div>
                <div>
                    🔵 <span style="color: #58a6ff;">Victim (الضحية):</span> 
                    <span style="color: #f0f6fc; background-color: #21262d; padding: 2px 8px; border-radius: 4px; border: 1px solid #1f6feb;">
                        {victim_name}
                    </span>
                </div>
                <div>
                    📱 <span style="color: #8b949e;">Device Role:</span> 
                    <span style="color: #f0f6fc; background-color: #21262d; padding: 2px 8px; border-radius: 4px; border: 1px solid #30363d;">
                        {device_owner_label}
                    </span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# OSINT & SOCIAL MEDIA RECONNAISSANCE ENGINE
# ==============================================================================
def check_social_media_account(platform_name, profile_url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ForensicSuite/1.0'}
    try:
        response = requests.get(profile_url, headers=headers, timeout=4, allow_redirects=True)
        if response.status_code == 200:
            return "EXISTS / ACTIVE", profile_url
        elif response.status_code == 404:
            return "NOT FOUND", profile_url
        else:
            return f"UNCERTAIN ({response.status_code})", profile_url
    except requests.RequestException:
        return "CHECK FAILED / BLOCKED", profile_url

def extract_usernames_and_handles(text):
    mentions = re.findall(r'@([a-zA-Z0-9_]{3,30})', text)
    emails = re.findall(r'([a-zA-Z0-9._%+-]+)@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    explicit_users = re.findall(r'\b(?:username|user|المستخدم|يوزر|حساب|اليوزر)\s*[:=]?\s*([a-zA-Z0-9._-]+)\b', text, re.IGNORECASE)
    
    combined = set(mentions + emails + explicit_users)
    ignored = {'gmail', 'yahoo', 'hotmail', 'outlook', 'icloud', 'com', 'org', 'net'}
    return [u for u in combined if u.lower() not in ignored and len(u) >= 3]

# ==============================================================================
# ADVANCED ANALYTICS ENGINES
# ==============================================================================
def analyze_chat_threat_score(text, lang_choice, device_role):
    high_risk_words = ['تهديد', 'ابتزاز', 'فلوس', 'حساب', 'تحويل', 'اخترقت', 'اطرش', 'صورك', 'fadiha', 'فضيحة', 'money', 'blackmail', 'hack', 'transfer', 'wire', 'scam', '凍結', '不正', '脅迫', '金']
    med_risk_words = ['رابط', 'يوزر', 'باسورد', 'ايميل', 'كود', 'واتساب', 'link', 'password', 'code', 'verify', 'user', 'whatsapp', 'リンク', '口座']
    
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
        return ("SUSPICIOUS IP" if lang_choice == "English" else "IP مشبوه"), 70, "Flagged Infrastructure routing"
    suspicious_keywords = ['login', 'verify', 'update', 'bank', 'secure', 'free', 'gift', 'crypto', 'secure-bank']
    score = 0
    reasons = []
    for word in suspicious_keywords:
        if word in item.lower():
            score += 25
            reasons.append(f"Keyword '{word}'")
    if score >= 50:
        return ("HIGH RISK" if lang_choice == "English" else "خطورة عالية"), min(score, 100), ", ".join(reasons)
    return ("SAFE" if lang_choice == "English" else "آمن"), score, "-"

# ==============================================================================
# REPORTLAB PDF GENERATOR FUNCTION
# ==============================================================================
def create_reportlab_pdf(case_id, officer, suspect, victim, app_src, dev_role, file_hash, score, score_label, ibans, emails, phones, urls, total_money, recon_data, audit_logs):
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
        [Paragraph("<b>Victim / Complainant:</b>", body_style), Paragraph(str(victim), body_style)],
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
        [Paragraph(f"<b>{score}%</b>", body_style), Paragraph(str(score_label), body_style), Paragraph(f"{total_money} BHD / Units", body_style)]
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

    story.append(Paragraph("3. Extracted Forensic Indicators", h2_style))
    artifacts_text = f"""
    • <b>IBAN Accounts ({len(ibans)}):</b> {', '.join(ibans) if ibans else 'None Identified'}<br/>
    • <b>Phone Numbers ({len(phones)}):</b> {', '.join(phones) if phones else 'None Identified'}<br/>
    • <b>Email Addresses ({len(emails)}):</b> {', '.join(emails) if emails else 'None Identified'}<br/>
    • <b>Network/IP Indicators ({len(urls)}):</b> {', '.join(urls) if urls else 'None Identified'}
    """
    story.append(Paragraph(artifacts_text, body_style))
    story.append(Spacer(1, 8))

    story.append(Paragraph("4. OSINT Social Media Reconnaissance Results", h2_style))
    if recon_data:
        osint_table_data = [[Paragraph("<b>Platform</b>", body_style), Paragraph("<b>Status</b>", body_style), Paragraph("<b>Profile Endpoint</b>", body_style)]]
        for r in recon_data:
            osint_table_data.append([
                Paragraph(str(r.get("Platform / Network", r.get("Platform", ""))), body_style),
                Paragraph(str(r.get("Recon Status", r.get("Status", ""))), body_style),
                Paragraph(str(r.get("Profile Link", r.get("URL", ""))), body_style)
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

    story.append(Paragraph("5. Digital Chain of Custody & Legal Audit Trail", h2_style))
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
# BILINGUAL LOCALIZATION LEXICON
# ==============================================================================
LEXICON = {
    "English": {
        "title": "🛡️ Chat-Forensics Intelligence Suite (CFIS)",
        "sub": "CID Anti-Electronic Crime Directorate | Advanced Multi-Platform Forensic Triage V6",
        "sb_header": "📁 Investigative Case Metadata",
        "sb_case": "Official Case Number:",
        "sb_officer": "Investigating Officer Name / Rank:",
        "sb_suspect": "Suspect Identifier / Alias:",
        "sb_victim": "Victim / Complainant Name:",
        "sb_app_src": "Select Chat App Source:",
        "sb_dev_role": "Select Device Owner Role:",
        "upload_lbl": "Upload Exported Chat File (.txt or .json)",
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
        "tab_social": "📲 Social Media & OSINT Recon",
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
        "kw_inspector_title": "🔍 Multi-Contact Inspector & Color-Coded Map",
        "load_archive_btn": "Load Target Archive",
        "archive_search_lbl": "Recall previous case file by ID:",
        "stored_records_lbl": "🗄️ Currently Stored Central Records:",
        "no_evidence_msg": "⚠️ Please upload a chat file (.txt / .json) first to begin the forensic evaluation.",
        "active_trans_msg": "📊 The forensic analytics matrix is currently operating on the [Approved Translated Text].",
        "no_participants": "No structured participants extracted.",
        "osint_header": "🔎 Target User Handle Detection & Cross-Platform Recon",
        "osint_btn": "⚡ Run Automated Social Media Footprint Recon",
        "osint_custom_input": "Or enter a specific suspect handle to investigate:",
        "col_platform": "Platform / Network",
        "col_profile": "Profile Link",
        "col_osint_status": "Recon Status"
    },
    "العربية": {
        "title": "🛡️ المنظومة الذكية لتحليل أدلة المحادثات الرقمية (CFIS)",
        "sub": "إدارة مكافحة الجرائم الإلكترونية | مختبر الأدلة الرقمية متعدد المنصات",
        "sb_header": "📁 بيانات ملف القضية الجنائية",
        "sb_case": "رقم القضية الرسمي:",
        "sb_officer": "اسم ورتبة ضابط التحقيق:",
        "sb_suspect": "هوية / اسم الشهرة للمشتبه به:",
        "sb_victim": "اسم المجني عليه / الضحية:",
        "sb_app_src": "اختر تطبيق المحادثة المصدر:",
        "sb_dev_role": "صفة صاحب الجهاز المظبوط:",
        "upload_lbl": "رفع سجل المحادثات المصدر (.txt أو .json)",
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
        "tab_social": "📲 حسابات التواصل والاستخبارات المفتوحة",
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
        "col_flags": "مؤشرات الشبهة المرصودة",
        "clear_btn": "🗑️ مسح الملف الحالي",
        "checksum_lbl": "📄 بصمة الدليل الرقمي وضمان النزاهة",
        "trans_header": "🔠 كاشف ومترجم اللغات الجنائية الفوري",
        "trans_lbl": "اختر لغة ملف المحادثة الأصلي (Source Language):",
        "trans_btn": "🔮 ترجمة وتحديث مصفوفة التحليل الجنائي فوراً",
        "trans_back": "🔄 العودة للملف الأصلي (الغير مترجم)",
        "trans_matrix_lbl": "نص المحادثة المترجم الحالي:",
        "kw_inspector_title": "🔍 مستعرض تظليل أطراف المحادثة والكلمات المفتاحية",
        "load_archive_btn": "تحميل الأرشيف المستهدف",
        "archive_search_lbl": "استدعاء قضية مؤرشفة سابقة برقم الملف:",
        "stored_records_lbl": "🗄️ السجلات المركزية المخزنة حالياً:",
        "no_evidence_msg": "⚠️ الرجاء رفع ملف المحادثة (.txt / .json) أولاً للبدء بالفحص والتحليل الجنائي المتقدم.",
        "active_trans_msg": "📊 مصفوفة التحليل تعمل حالياً بناءً على [النص المترجم المعتمد].",
        "no_participants": "لم يتم استخراج أطراف مهيكلة للمحادثة.",
        "osint_header": "🔎 رصد المعرفات واستخبارات حسابات التواصل الاجتماعي",
        "osint_btn": "⚡ تشغيل فحص البصمة الرقمية على المنصات",
        "osint_custom_input": "أو أدخل معرفاً (Username) محدداً للمشتبه به للبحث عنه:",
        "col_platform": "منصة التواصل الاجتماعي",
        "col_profile": "رابط الحساب المرصود",
        "col_osint_status": "نتيجة التتبع والاستخبار"
    }
}

# ==============================================================================
# STATE INITIALIZATION & STREAMLIT UI RENDER
# ==============================================================================
st.set_page_config(page_title="CFIS - Advanced Forensic Suite", layout="wide")
apply_custom_theme()

if 'active_chat_content' not in st.session_state:
    st.session_state['active_chat_content'] = None
if 'active_file_hash' not in st.session_state:
    st.session_state['active_file_hash'] = "NO_EVIDENCE_STREAM"
if 'translated_chat_content' not in st.session_state:
    st.session_state['translated_chat_content'] = None
if 'last_osint_results' not in st.session_state:
    st.session_state['last_osint_results'] = []
if 'audit_trail' not in st.session_state:
    st.session_state['audit_trail'] = []

lang = st.sidebar.selectbox("🌐 UI Language / لغة الواجهة", ["العربية", "English"])
tx = LEXICON[lang]

st.title(tx["title"])
st.subheader(tx["sub"])
st.markdown("<hr style='border-color: #30363d;'>", unsafe_allow_html=True)

st.sidebar.header(tx["sb_header"])
case_id = st.sidebar.text_input(tx["sb_case"], value="2026/CID/1054")
investigator = st.sidebar.text_input(tx["sb_officer"], value="Lt. Dana Khalifa")
suspect_name = st.sidebar.text_input(tx["sb_suspect"], value="Target_Alpha")
victim_name = st.sidebar.text_input(tx["sb_victim"], value="Complainant_Beta")

app_source = st.sidebar.selectbox(
    tx["sb_app_src"], 
    ["WhatsApp (.txt)", "Telegram (.json)", "Instagram DMs (.json)", "Facebook Messenger (.json)"]
)

device_role = st.sidebar.selectbox(
    tx["sb_dev_role"], 
    ["🔴 Suspect / Criminal Device", "🔵 Victim Device"]
)

def add_audit_entry(phase, action, officer, file_hash):
    st.session_state['audit_trail'].append({
        "phase": phase,
        "action": action,
        "timestamp": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
        "officer": officer,
        "hash_stamp": file_hash
    })

# File Upload Processing
uploaded_file = st.file_uploader(tx["upload_lbl"], type=['txt', 'json'])

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
    raw_text = parse_uploaded_chat(file_bytes, app_source)
    st.session_state['active_chat_content'] = raw_text
    st.session_state['active_file_hash'] = hashlib.sha256(file_bytes).hexdigest()
    
    if not st.session_state['audit_trail']:
        add_audit_entry("INGESTION", f"Loaded File: {uploaded_file.name}", investigator, st.session_state['active_file_hash'])

# Main Content Routing
chat_to_analyze = st.session_state['translated_chat_content'] if st.session_state['translated_chat_content'] else st.session_state['active_chat_content']

if chat_to_analyze:
    st.info(f"{tx['checksum_lbl']}: `{st.session_state['active_file_hash']}`")
    
    if st.session_state['translated_chat_content']:
        st.success(tx["active_trans_msg"])

    # Language Translator Block
    with st.expander(tx["trans_header"]):
        t_col1, t_col2 = st.columns([2, 1])
        with t_col1:
            source_lang = st.selectbox(tx["trans_lbl"], ["auto", "ar", "en", "ja", "ru", "zh-CN", "fa", "ur"])
        with t_col2:
            st.write("")
            st.write("")
            if st.button(tx["trans_btn"]):
                with st.spinner("Translating forensic text stream..."):
                    try:
                        translated = GoogleTranslator(source=source_lang, target='en').translate(st.session_state['active_chat_content'])
                        st.session_state['translated_chat_content'] = translated
                        add_audit_entry("TRANSLATION", f"Translated from {source_lang} to en", investigator, st.session_state['active_file_hash'])
                        st.rerun()
                    except Exception as e:
                        st.error(f"Translation Error: {e}")
            if st.session_state['translated_chat_content']:
                if st.button(tx["trans_back"]):
                    st.session_state['translated_chat_content'] = None
                    st.rerun()

    # Threat Analytics Engine Evaluation
    threat_score, threat_label = analyze_chat_threat_score(chat_to_analyze, lang, device_role)
    st.markdown(f"### {tx['threat_idx']} `{threat_score}%` {tx['forensic_triage_res']} **{threat_label}**")

    # Artifact Extraction Regex
    iban_list = list(set(re.findall(r'\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b', chat_to_analyze)))
    phone_list = list(set(re.findall(r'\+?\d{8,15}', chat_to_analyze)))
    email_list = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', chat_to_analyze)))
    url_list = list(set(re.findall(r'https?://[^\s]+|\b(?:\d{1,3}\.){3}\d{1,3}\b', chat_to_analyze)))
    money_amounts, total_money = extract_financial_amounts(chat_to_analyze)

    # --------------------------------------------------------------------------
    # ARTIFACT LEGEND & VICTIM / SUSPECT IDENTITY BLOCK
    # --------------------------------------------------------------------------
    st.subheader(tx["kw_inspector_title"])
    contact_color_map = extract_contacts_map(chat_to_analyze)
    
    # Render Legend + Suspect and Victim Identification Block
    render_artifact_legend_with_roles(
        suspect_name=suspect_name, 
        device_role=device_role,
        victim_name=victim_name
    )

    # Render Color-Coded Chat Output
    highlighted_html = generate_keyword_highlight_html(chat_to_analyze, contact_color_map)
    st.markdown(f'<div class="highlight-box">{highlighted_html}</div>', unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    # Psychological Intelligence Section
    st.subheader(tx["intel_header"])
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        st.markdown(f'<div class="forensic-card"><h4>{tx["card_tone"]}</h4>', unsafe_allow_html=True)
        tone_data = analyze_sentiment_and_tone(chat_to_analyze)
        df_tone = pd.DataFrame(list(tone_data.items()), columns=['Tone', 'Percentage'])
        fig_tone = px.pie(df_tone, values='Percentage', names='Tone', hole=0.4, color_discrete_sequence=['#ea580c', '#3b82f6', '#10b981'])
        fig_tone.update_layout(margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#c9d1d9")
        st.plotly_chart(fig_tone, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_b:
        st.markdown(f'<div class="forensic-card"><h4>{tx["card_financial"]}</h4>', unsafe_allow_html=True)
        st.metric("Total Demanded Amount", f"{total_money} BHD / Units")
        st.write("Extracted Amounts Sequence:")
        st.write(money_amounts if money_amounts else "No explicit financial numbers detected.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_c:
        st.markdown(f'<div class="forensic-card"><h4>{tx["card_speaker"]}</h4>', unsafe_allow_html=True)
        if contact_color_map:
            speaker_counts = {contact: chat_to_analyze.count(contact) for contact in contact_color_map.keys()}
            df_speakers = pd.DataFrame(list(speaker_counts.items()), columns=['Speaker', 'Messages'])
            fig_speakers = px.bar(df_speakers, x='Speaker', y='Messages', color='Speaker')
            fig_speakers.update_layout(margin=dict(t=0, b=0, l=0, r=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#c9d1d9", showlegend=False)
            st.plotly_chart(fig_speakers, use_container_width=True)
        else:
            st.write(tx["no_participants"])
        st.markdown('</div>', unsafe_allow_html=True)

    # Artifact Tabs Section
    st.subheader(tx["art_title"])
    tab1, tab2, tab3, tab4, tab5 = st.tabs([tx["tab_bank"], tx["tab_phone"], tx["tab_url"], tx["tab_social"], tx["tab_vault"]])

    with tab1:
        if iban_list:
            iban_data = []
            for iban in iban_list:
                match = check_cross_case(iban)
                status = f"⚠️ MATCH: Case {match[0]} ({match[1]})" if match else "✅ Clean / No History"
                iban_data.append({tx["col_iban"]: iban, tx["col_status"]: status})
            st.dataframe(pd.DataFrame(iban_data), use_container_width=True)
        else:
            st.info("No IBAN account numbers detected.")

    with tab2:
        if phone_list or email_list:
            p_data = []
            for p in phone_list:
                match = check_cross_case(p)
                status = f"⚠️ MATCH: Case {match[0]} ({match[1]})" if match else "✅ Clean"
                p_data.append({"Indicator": p, "Type": "Phone", tx["col_match"]: status})
            for e in email_list:
                match = check_cross_case(e)
                status = f"⚠️ MATCH: Case {match[0]} ({match[1]})" if match else "✅ Clean"
                p_data.append({"Indicator": e, "Type": "Email", tx["col_match"]: status})
            st.dataframe(pd.DataFrame(p_data), use_container_width=True)
        else:
            st.info("No telephony or email markers detected.")

    with tab3:
        if url_list:
            u_data = []
            for item in url_list:
                risk_lvl, u_score, flags = analyze_url_or_ip(item, lang)
                u_data.append({
                    tx["col_url"]: item,
                    tx["col_risk"]: risk_lvl,
                    tx["col_score"]: u_score,
                    tx["col_flags"]: flags
                })
            st.dataframe(pd.DataFrame(u_data), use_container_width=True)
        else:
            st.info("No URLs or IP addresses detected.")

    with tab4:
        st.write(f"### {tx['osint_header']}")
        extracted_handles = extract_usernames_and_handles(chat_to_analyze)
        custom_handle = st.text_input(tx["osint_custom_input"], value=extracted_handles[0] if extracted_handles else "")
        
        if st.button(tx["osint_btn"]):
            target = custom_handle if custom_handle else (extracted_handles[0] if extracted_handles else "")
            if target:
                with st.spinner(f"Running automated OSINT footprint scan for '{target}'..."):
                    platforms = {
                        "Instagram": f"https://www.instagram.com/{target}/",
                        "X (Twitter)": f"https://x.com/{target}",
                        "Telegram Profile": f"https://t.me/{target}",
                        "GitHub": f"https://github.com/{target}",
                        "TikTok": f"https://www.tiktok.com/@{target}"
                    }
                    recon_results = []
                    for name, url in platforms.items():
                        status, link = check_social_media_account(name, url)
                        recon_results.append({
                            tx["col_platform"]: name,
                            tx["col_osint_status"]: status,
                            tx["col_profile"]: link
                        })
                    st.session_state['last_osint_results'] = recon_results
                    add_audit_entry("OSINT", f"Scanned handle: {target}", investigator, st.session_state['active_file_hash'])
            else:
                st.warning("No handle detected or entered for recon.")
                
        if st.session_state['last_osint_results']:
            st.dataframe(pd.DataFrame(st.session_state['last_osint_results']), use_container_width=True)

    with tab5:
        st.write(f"### {tx['tab_vault']}")
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            if st.button(tx["save_vault_btn"]):
                if save_full_case(case_id, investigator, suspect_name, app_source, device_role, st.session_state['active_file_hash'], chat_to_analyze):
                    add_audit_entry("ARCHIVE", f"Saved case {case_id} to database", investigator, st.session_state['active_file_hash'])
                    st.success(f"Case {case_id} successfully archived into local SQLite vault.")
                else:
                    st.error("Failed to archive case.")
        with col_v2:
            search_case = st.text_input(tx["archive_search_lbl"], value=case_id)
            if st.button(tx["load_archive_btn"]):
                record = load_full_case(search_case)
                if record:
                    st.session_state['active_chat_content'] = record[0]
                    st.session_state['translated_chat_content'] = None
                    st.session_state['active_file_hash'] = record[3]
                    add_audit_entry("RECALL", f"Loaded archived case {search_case}", investigator, record[3])
                    st.success(f"Case {search_case} loaded successfully.")
                    st.rerun()
                else:
                    st.error("Case ID not found in local vault.")

        st.markdown("<hr style='border-color: #30363d;'>", unsafe_allow_html=True)
        st.write(f"#### {tx['stored_records_lbl']}")
        st.dataframe(get_all_indicators(), use_container_width=True)

    # PDF Generator Action Bar
    st.markdown("<br/>", unsafe_allow_html=True)
    pdf_bytes = create_reportlab_pdf(
        case_id, investigator, suspect_name, victim_name, app_source, device_role, 
        st.session_state['active_file_hash'], threat_score, threat_label, 
        iban_list, email_list, phone_list, url_list, total_money, 
        st.session_state['last_osint_results'], st.session_state['audit_trail']
    )
    
    st.download_button(
        label=tx["pdf_btn"],
        data=pdf_bytes,
        file_name=f"Forensic_Report_{case_id.replace('/', '_')}.pdf",
        mime="application/pdf"
    )

else:
    st.warning(tx["no_evidence_msg"])

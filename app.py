import hashlib
import io
import json
import re
import sqlite3
from datetime import datetime, timezone

from deep_translator import GoogleTranslator
import pandas as pd
import plotly.express as px
import requests

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import streamlit as st

# ==============================================================================
# COLOR PALETTE & THEME
# ==============================================================================
CONTACT_COLORS = [
    {"bg": "#1e3a8a", "border": "#3b82f6", "text": "#93c5fd"},
    {"bg": "#701a75", "border": "#d946ef", "text": "#f5d0fe"},
    {"bg": "#064e3b", "border": "#10b981", "text": "#a7f3d0"},
    {"bg": "#78350f", "border": "#f59e0b", "text": "#fde68a"},
    {"bg": "#831843", "border": "#ec4899", "text": "#fbcfe8"},
    {"bg": "#134e4a", "border": "#14b8a6", "text": "#99f6e4"},
    {"bg": "#7c2d12", "border": "#ea580c", "text": "#ffedd5"},
]


def apply_custom_theme():
  st.markdown(
      """
        <style>
            .stApp { background-color: #0d1117; color: #c9d1d9; font-family: 'Segoe UI', sans-serif; }
            h1 { color: #58a6ff !important; font-weight: 700 !important; }
            h2, h3, h4 { color: #f0f6fc !important; font-weight: 600 !important; }
            .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: #161b22; padding: 8px; border-radius: 10px; border: 1px solid #30363d; }
            .stTabs [aria-selected="true"] { background-color: #1f6feb !important; color: #ffffff !important; }
            .forensic-card { background-color: #161b22; border: 1px solid #30363d; padding: 20px; border-radius: 12px; margin-bottom: 15px; }
            .stButton>button { background: linear-gradient(135deg, #1f6feb 0%, #115293 100%) !important; color: white !important; border: none !important; border-radius: 8px !important; }
            section[data-testid="stSidebar"] { background-color: #090d13 !important; border-right: 1px solid #30363d; }
            .highlight-box { background-color: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px; max-height: 400px; overflow-y: auto; font-size: 13px; line-height: 1.8; }
            .contact-badge { padding: 2px 8px; border-radius: 4px; font-weight: bold; margin-right: 6px; display: inline-block; border: 1px solid; }
            .hl-red { background-color: #7d1a1a; color: #ff9999; padding: 2px 4px; border-radius: 3px; font-weight: bold; }
            .hl-yellow { background-color: #7d601a; color: #ffe066; padding: 2px 4px; border-radius: 3px; font-weight: bold; }
            .hl-blue { background-color: #1a4d7d; color: #99ccff; padding: 2px 4px; border-radius: 3px; font-weight: bold; }
        </style>
    """,
      unsafe_allow_html=True,
  )


# ==============================================================================
# DATABASE ENGINE
# ==============================================================================
def init_db():
  conn = sqlite3.connect("cfis_local_vault.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS historical_markers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator TEXT UNIQUE,
            indicator_type TEXT,
            case_number TEXT,
            officer_assigned TEXT,
            date_logged TEXT
        )
    """)
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases_archive (
            case_number TEXT PRIMARY KEY,
            officer_assigned TEXT,
            suspect_name TEXT,
            victim_name TEXT,
            app_source TEXT,
            device_role TEXT,
            file_hash TEXT,
            chat_content TEXT,
            date_saved TEXT
        )
    """)
  mock_data = [
      ("BH12BBAN00000000123456", "IBAN", "2026/CID/894", "Lt. Jasim", "2026-04-12"),
      ("+97333123456", "Phone", "2026/CID/412", "Sgt. Ali", "2026-05-19"),
      ("scammer99@gmail.com", "Email", "2026/CID/894", "Lt. Jasim", "2026-04-12"),
      ("192.168.1.105", "IP Address", "2026/CID/711", "Lt. Dana", "2026-07-10"),
  ]
  try:
    cursor.executemany(
        "INSERT OR IGNORE INTO historical_markers (indicator, indicator_type, case_number, officer_assigned, date_logged) VALUES (?, ?, ?, ?, ?)",
        mock_data,
    )
    conn.commit()
  except sqlite3.Error:
    pass
  finally:
    conn.close()


init_db()


def check_cross_case(indicator):
  conn = sqlite3.connect("cfis_local_vault.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT case_number, officer_assigned FROM historical_markers WHERE indicator = ?",
      (indicator,),
  )
  result = cursor.fetchone()
  conn.close()
  return result


def save_full_case(case_num, officer, suspect, victim, app_src, dev_role, f_hash, content):
  conn = sqlite3.connect("cfis_local_vault.db")
  cursor = conn.cursor()
  try:
    cursor.execute(
        """
            INSERT OR REPLACE INTO cases_archive (case_number, officer_assigned, suspect_name, victim_name, app_source, device_role, file_hash, chat_content, date_saved)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_num,
            officer,
            suspect,
            victim,
            app_src,
            dev_role,
            f_hash,
            content,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    return True
  except sqlite3.Error:
    return False
  finally:
    conn.close()


def load_full_case(case_num):
  conn = sqlite3.connect("cfis_local_vault.db")
  cursor = conn.cursor()
  cursor.execute(
      "SELECT chat_content, officer_assigned, suspect_name, victim_name, file_hash, app_source, device_role FROM cases_archive WHERE case_number = ?",
      (case_num,),
  )
  result = cursor.fetchone()
  conn.close()
  return result


def get_all_indicators():
  conn = sqlite3.connect("cfis_local_vault.db")
  df = pd.read_sql_query("SELECT * FROM historical_markers ORDER BY id DESC", conn)
  conn.close()
  return df


# ==============================================================================
# PARSERS & ANALYTICS
# ==============================================================================
def parse_uploaded_chat(file_bytes, app_source):
  if app_source == "WhatsApp (.txt)":
    return file_bytes.decode("utf-8", errors="ignore")
  try:
    json_data = json.loads(file_bytes.decode("utf-8", errors="ignore"))
    parsed_lines = []
    if app_source == "Telegram (.json)":
      for msg in json_data.get("messages", []):
        if msg.get("type") == "message":
          sender = msg.get("from", "Unknown")
          date = msg.get("date", "")
          text = msg.get("text", "")
          if isinstance(text, list):
            text = "".join([t["text"] if isinstance(t, dict) else str(t) for t in text])
          parsed_lines.append(f"[{date}] {sender}: {text}")
    elif app_source in ["Instagram DMs (.json)", "Facebook Messenger (.json)"]:
      for msg in reversed(json_data.get("messages", [])):
        sender = msg.get("sender_name", "Unknown")
        ms = msg.get("timestamp_ms", 0)
        date = (
            datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            if ms
            else ""
        )
        parsed_lines.append(f"[{date}] {sender}: {msg.get('content', '')}")
    return "\n".join(parsed_lines) if parsed_lines else file_bytes.decode("utf-8", errors="ignore")
  except Exception:
    return file_bytes.decode("utf-8", errors="ignore")


def extract_contacts_map(chat_text):
  senders_raw = re.findall(r'-\s([^:]+):|\]\s([^:]+):|\[[^\]]+\]\s([^:]+):', chat_text)
  unique_senders = []
  for s in senders_raw:
    name = s[0] if s[0] else (s[1] if s[1] else s[2])
    if name and name.strip() not in unique_senders:
      unique_senders.append(name.strip())
  return {sender: CONTACT_COLORS[i % len(CONTACT_COLORS)] for i, sender in enumerate(unique_senders)}


def generate_keyword_highlight_html(chat_text, contact_color_map):
  red_words = ['تهديد', 'ابتزاز', 'فلوس', 'اخترقت', 'اطرش', 'صورك', 'fadiha', 'فضيحة', 'blackmail', 'hack', 'scam', '脅迫', 'فضايح', 'بفضحك', 'انشر']
  yellow_words = ['حساب', 'تحويل', 'دينار', 'كاش', 'IBAN', 'BD', 'BHD', 'money', 'transfer', 'wire', 'pay', 'cash', 'مركز', 'بنك']
  blue_words = ['رابط', 'يوزر', 'باسورد', 'ايميل', 'كود', 'واتساب', 'link', 'password', 'code', 'verify', 'user', 'whatsapp']

  lines = chat_text.split('\n')
  highlighted_lines = []
  for line in lines:
    escaped = line.replace('<', '&lt;').replace('>', '&gt;')
    for contact, c_style in contact_color_map.items():
      if contact in escaped:
        badge = f'<span class="contact-badge" style="background-color: {c_style["bg"]}; border-color: {c_style["border"]}; color: {c_style["text"]};">{contact}</span>'
        escaped = escaped.replace(contact, badge, 1)
    for w in red_words:
      escaped = re.sub(f'(?i)({re.escape(w)})', r'<span class="hl-red">\1</span>', escaped)
    for w in yellow_words:
      escaped = re.sub(f'(?i)({re.escape(w)})', r'<span class="hl-yellow">\1</span>', escaped)
    for w in blue_words:
      escaped = re.sub(f'(?i)({re.escape(w)})', r'<span class="hl-blue">\1</span>', escaped)
    highlighted_lines.append(escaped)
  return '<br/>'.join(highlighted_lines)


def check_social_media_account(platform_name, profile_url):
  headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ForensicSuite/1.0'}
  try:
    res = requests.get(profile_url, headers=headers, timeout=4, allow_redirects=True)
    if res.status_code == 200:
      return 'EXISTS / ACTIVE', profile_url
    elif res.status_code == 404:
      return 'NOT FOUND', profile_url
    return f'UNCERTAIN ({res.status_code})', profile_url
  except requests.RequestException:
    return 'CHECK FAILED / BLOCKED', profile_url


def extract_usernames_and_handles(text):
  mentions = re.findall(r'@([a-zA-Z0-9_]{3,30})', text)
  emails = re.findall(r'([a-zA-Z0-9._%+-]+)@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
  explicit_users = re.findall(r'\b(?:username|user|المستخدم|يوزر|حساب|اليوزر)\s*[:=]?\s*([a-zA-Z0-9._-]+)\b', text, re.IGNORECASE)
  combined = set(mentions + emails + explicit_users)
  ignored = {'gmail', 'yahoo', 'hotmail', 'outlook', 'icloud', 'com', 'org', 'net'}
  return [u for u in combined if u.lower() not in ignored and len(u) >= 3]


def analyze_chat_threat_score(text, lang_choice, device_role):
  high_risk = ['تهديد', 'ابتزاز', 'فلوس', 'حساب', 'تحويل', 'اخترقت', 'اطرش', 'صورك', 'fadiha', 'فضيحة', 'money', 'blackmail', 'hack', 'transfer', 'wire', 'scam']
  med_risk = ['رابط', 'يوزر', 'باسورد', 'ايميل', 'كود', 'واتساب', 'link', 'password', 'code', 'verify', 'user', 'whatsapp']
  high_hits = sum(1 for w in high_risk if w in text.lower())
  med_hits = sum(1 for w in med_risk if w in text.lower())
  multiplier = 1.2 if ("Suspect" in device_role or "المشتبه" in device_role) else 1.0
  score = min(int(((high_hits * 15) + (med_hits * 7)) * multiplier), 100)
  if score >= 60:
    return score, ("CRITICAL RISK" if lang_choice == "English" else "مستوى خطر حرج")
  elif score >= 25:
    return score, ("MEDIUM RISK" if lang_choice == "English" else "مستوى خطر متوسط")
  return score, ("LOW RISK" if lang_choice == "English" else "مستوى خطر منخفض")


def analyze_sentiment_and_tone(text):
  t_words = ['تهديد', 'ابتزاز', 'فضيحة', 'بفضحك', 'انشر', 'صورك', 'blackmail', 'expose', 'threat']
  f_words = ['خايف', 'ارجوك', 'لا تنشر', 'ستر', 'تكفى', 'please', 'dont', 'afraid', 'stop']
  m_words = ['تحويل', 'فلوس', 'دينار', 'حساب', 'كاش', 'money', 'cash', 'pay', 'transfer']
  t_count = sum(1 for w in t_words if w in text.lower())
  f_count = sum(1 for w in f_words if w in text.lower())
  m_count = sum(1 for w in m_words if w in text.lower())
  total = max(t_count + f_count + m_count, 1)
  return {
      "Threat Tone": round((t_count / total) * 100, 1),
      "Victim Response": round((f_count / total) * 100, 1),
      "Financial Demands": round((m_count / total) * 100, 1),
  }


def extract_financial_amounts(text):
  amounts = re.findall(r'\b(\d+(?:\.\d+)?)\s*(?:دينار|بحريني|BD|BHD|dollar|\$|euro)\b', text.lower())
  return amounts, sum(float(a) for a in amounts)


def analyze_url_or_ip(item, lang_choice):
  if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', item):
    return ("SUSPICIOUS IP" if lang_choice == "English" else "IP مشبوه"), 70, "Flagged Infrastructure"
  suspicious = ['login', 'verify', 'update', 'bank', 'secure', 'free', 'gift', 'crypto']
  score = sum(25 for w in suspicious if w in item.lower())
  if score >= 50:
    return ("HIGH RISK" if lang_choice == "English" else "خطورة عالية"), min(score, 100), "Suspicious keywords found"
  return ("SAFE" if lang_choice == "English" else "آمن"), score, "None"


# ==============================================================================
# REPORTLAB PDF GENERATOR
# ==============================================================================
def create_reportlab_pdf(
    case_id,
    officer,
    suspect,
    victim,
    extracted_participants,
    app_src,
    dev_role,
    file_hash,
    score,
    score_label,
    tone_metrics,
    ibans,
    emails,
    phones,
    urls,
    total_money,
    recon_data,
    audit_logs,
):
  buffer = io.BytesIO()
  doc = SimpleDocTemplate(
      buffer,
      pagesize=letter,
      rightMargin=36,
      leftMargin=36,
      topMargin=36,
      bottomMargin=36,
  )
  styles = getSampleStyleSheet()

  title_style = ParagraphStyle(
      'DocTitle', parent=styles['Heading1'], fontSize=16, leading=20, alignment=1, textColor=colors.HexColor('#0f2b48')
  )
  subtitle_style = ParagraphStyle(
      'DocSubTitle', parent=styles['Normal'], fontSize=9, leading=12, alignment=1, textColor=colors.HexColor('#4a5568')
  )
  h2_style = ParagraphStyle(
      'SectionHeader', parent=styles['Heading2'], fontSize=11, leading=15, textColor=colors.HexColor('#1a365d'), spaceBefore=10, spaceAfter=4
  )
  body_style = ParagraphStyle(
      'BodyTextCustom', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.HexColor('#2d3748')
  )

  story = []
  story.append(Paragraph("DIGITAL FORENSICS INVESTIGATION REPORT", title_style))
  story.append(Paragraph("GENERAL DIRECTORATE OF ANTI-CORRUPTION & ECONOMIC & ELECTRONIC SECURITY", subtitle_style))
  story.append(Spacer(1, 10))

  meta_data = [
      [Paragraph("<b>Case Number:</b>", body_style), Paragraph(str(case_id), body_style)],
      [Paragraph("<b>Investigating Officer:</b>", body_style), Paragraph(str(officer), body_style)],
      [Paragraph("<b>Suspect / Target Alias:</b>", body_style), Paragraph(str(suspect), body_style)],
      [Paragraph("<b>Victim / Complainant:</b>", body_style), Paragraph(str(victim), body_style)],
      [Paragraph("<b>App Source & Role:</b>", body_style), Paragraph(f"{app_src} | Role: {dev_role}", body_style)],
      [Paragraph("<b>Evidence Hash (SHA-256):</b>", body_style), Paragraph(str(file_hash), body_style)],
      [Paragraph("<b>Generated Timestamp:</b>", body_style), Paragraph(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), body_style)],
  ]
  meta_table = Table(meta_data, colWidths=[140, 400])
  meta_table.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7fafc")),
          ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
          ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#edf2f7")),
          ("PADDING", (0, 0), (-1, -1), 4),
      ])
  )
  story.append(Paragraph("1. Case Metadata & Evidence Integrity", h2_style))
  story.append(meta_table)
  story.append(Spacer(1, 8))

  tone_str = ", ".join([f"{k}: {v}%" for k, v in tone_metrics.items()])
  risk_data = [
      [Paragraph("<b>Threat Index Score</b>", body_style), Paragraph("<b>Risk Classification</b>", body_style), Paragraph("<b>Financial Extortion Demand</b>", body_style)],
      [Paragraph(f"<b>{score}%</b>", body_style), Paragraph(str(score_label), body_style), Paragraph(f"{total_money} BHD / Units", body_style)],
  ]
  risk_table = Table(risk_data, colWidths=[180, 180, 180])
  risk_table.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ebf8ff")),
          ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e0")),
          ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
          ("ALIGN", (0, 0), (-1, -1), "CENTER"),
          ("PADDING", (0, 0), (-1, -1), 5),
      ])
  )
  story.append(Paragraph("2. Risk Assessment & Psychological Analysis", h2_style))
  story.append(risk_table)
  story.append(Paragraph(f"<b>Tone Metrics Breakdown:</b> {tone_str}", body_style))
  story.append(Spacer(1, 8))

  story.append(Paragraph("3. Extracted Forensic Indicators & Technical Identifiers", h2_style))
  artifacts_text = f"""
    • <b>IBAN Accounts ({len(ibans)}):</b> {', '.join(ibans) if ibans else 'None Identified'}<br/>
    • <b>Phone Numbers ({len(phones)}):</b> {', '.join(phones) if phones else 'None Identified'}<br/>
    • <b>Email Addresses ({len(emails)}):</b> {', '.join(emails) if emails else 'None Identified'}<br/>
    • <b>Extracted URLs & IP Addresses ({len(urls)}):</b> {', '.join(urls) if urls else 'None Identified'}
    """
  story.append(Paragraph(artifacts_text, body_style))
  story.append(Spacer(1, 8))

  story.append(Paragraph("4. OSINT Social Media Reconnaissance Results", h2_style))
  if recon_data:
    osint_table_data = [[
        Paragraph("<b>Target Handle</b>", body_style),
        Paragraph("<b>Platform</b>", body_style),
        Paragraph("<b>Status</b>", body_style),
        Paragraph("<b>Profile Endpoint</b>", body_style),
    ]]
    for item in recon_data:
      handle_val = item.get("Handle", item.get("المعرف", "N/A"))
      platform_val = item.get("Platform / Network", item.get("منصة التواصل الاجتماعي", item.get("Platform", "N/A")))
      status_val = item.get("Recon Status", item.get("نتيجة التتبع والاستخبار", item.get("Status", "N/A")))
      profile_val = item.get("Profile Link", item.get("رابط الحساب المرصود", item.get("URL", "N/A")))

      osint_table_data.append([
          Paragraph(str(handle_val), body_style),
          Paragraph(str(platform_val), body_style),
          Paragraph(str(status_val), body_style),
          Paragraph(str(profile_val), body_style),
      ])

    osint_table = Table(osint_table_data, colWidths=[100, 110, 110, 220])
    osint_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f7")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e0")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(osint_table)
  else:
    story.append(Paragraph("No automated OSINT platform scan was performed during this session.", body_style))

  story.append(Spacer(1, 8))

  story.append(Paragraph("5. Digital Chain of Custody & Action Audit Trail", h2_style))
  coc_table_data = [[
      Paragraph("<b>Phase</b>", body_style),
      Paragraph("<b>Action Performed</b>", body_style),
      Paragraph("<b>Timestamp (UTC)</b>", body_style),
      Paragraph("<b>Officer</b>", body_style),
      Paragraph("<b>Integrity Stamp</b>", body_style),
  ]]
  for log in audit_logs:
    coc_table_data.append([
        Paragraph(str(log.get("phase", "")), body_style),
        Paragraph(str(log.get("action", "")), body_style),
        Paragraph(str(log.get("timestamp", "")), body_style),
        Paragraph(str(log.get("officer", "")), body_style),
        Paragraph(f"<code>{str(log.get('hash_stamp', ''))[:10]}...</code>", body_style),
    ])

  coc_table = Table(coc_table_data, colWidths=[70, 150, 110, 90, 120])
  coc_table.setStyle(
      TableStyle([
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
          ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e0")),
          ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e0")),
          ("PADDING", (0, 0), (-1, -1), 4),
      ])
  )
  story.append(coc_table)

  story.append(Spacer(1, 15))
  story.append(Paragraph("<b>[ CONFIDENTIAL - OFFICIALLY VERIFIED FORENSIC CHAIN OF CUSTODY ]</b>", subtitle_style))

  doc.build(story)
  buffer.seek(0)
  return buffer.getvalue()


# ==============================================================================
# UI LEXICON
# ==============================================================================
LEXICON = {
    "English": {
        "title": "🛡️ Chat-Forensics Intelligence Suite (CFIS)",
        "sub": "CID Anti-Electronic Crime Directorate | Advanced Multi-Platform Forensic Triage V6",
        "sb_header": "📁 Case Identifiers",
        "sb_case": "Official Case Number:",
        "sb_officer": "Investigating Officer Name / Rank:",
        "sb_suspect": "Suspect Identifier / Alias:",
        "sb_victim": "Victim Identifier / Name:",
        "app_src_lbl": "Select Chat App Source:",
        "dev_role_lbl": "Select Device Owner Role:",
        "upload_lbl": "📥 Drag & Drop Exported Chat File Here (.txt or .json)",
        "save_vault_btn": "💾 Save Case to Central Archive Vault",
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
        "tab_vault": "📁 Central Vault Database",
        "pdf_btn": "📄 Export Official PDF Forensics Report",
        "col_iban": "IBAN Account Number",
        "col_status": "Cross-Case Match Status",
        "col_phone": "Phone Number",
        "col_match": "Database Match",
        "col_email": "Email Address",
        "col_url": "Extracted URL / IP",
        "col_risk": "Risk Assessment",
        "col_score": "Threat Score",
        "col_flags": "Risk Indicators Found",
        "clear_btn": "🗑️ Reset & Clear Evidence",
        "checksum_lbl": "📄 Evidence Digital Fingerprint & Integrity Check (SHA-256)",
        "trans_header": "🔠 Real-time Forensic Language Translator",
        "trans_lbl": "Select original chat file language (Source Language):",
        "trans_btn": "🔮 Translate & Update Forensic Matrix Now",
        "trans_back": "🔄 Revert to Original Untranslated File",
        "kw_inspector_title": "🔍 Multi-Contact Inspector & Color-Coded Map",
        "load_archive_btn": "Load Target Archive",
        "archive_search_lbl": "Recall previous case file by ID:",
        "stored_records_lbl": "🗄️ Currently Stored Central Records:",
        "no_evidence_msg": "⚠️ Please drag and drop a chat file (.txt / .json) below to begin the forensic evaluation.",
        "active_trans_msg": "📊 The forensic analytics matrix is currently operating on the [Approved Translated Text].",
        "no_participants": "No structured participants extracted.",
        "osint_header": "🔎 Target User Handle Detection & Cross-Platform Recon",
        "osint_btn": "⚡ Run Automated Social Media Footprint Recon",
        "osint_custom_input": "Or enter a specific suspect handle to investigate:",
        "col_platform": "Platform / Network",
        "col_profile": "Profile Link",
        "col_osint_status": "Recon Status",
        "parties_title": "👥 Identified Case Parties",
    },
    "العربية": {
        "title": "🛡️ المنظومة الذكية لتحليل أدلة المحادثات الرقمية (CFIS)",
        "sub": "إدارة مكافحة الجرائم الإلكترونية | مختبر الأدلة الرقمية متعدد المنصات",
        "sb_header": "📁 بيانات القضية الرئيسية",
        "sb_case": "رقم القضية الرسمي:",
        "sb_officer": "اسم ورتبة ضابط التحقيق:",
        "sb_suspect": "هوية / اسم الشهرة للمشتبه به:",
        "sb_victim": "اسم الضحية / المجني عليه:",
        "app_src_lbl": "اختر تطبيق المحادثة المصدر:",
        "dev_role_lbl": "صفة صاحب الجهاز المظبوط:",
        "upload_lbl": "📥 اسحب وأسقط ملف المحادثات هنا (.txt أو .json)",
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
        "tab_vault": "📁 قاعدة البيانات المركزية",
        "pdf_btn": "📄 تصدير التقرير الجنائي الرسمي (PDF)",
        "col_iban": "رقم الحساب البنكي (IBAN)",
        "col_status": "حالة المطابقة في القضايا الأخرى",
        "col_phone": "رقم الهاتف المرصود",
        "col_match": "المطابقة الجنائية",
        "col_email": "البريد الإلكتروني",
        "col_url": "الرابط أو الـ IP المستخرج",
        "col_risk": "تقييم مستوى الخطورة",
        "col_score": "درجة التهديد الرقمي",
        "col_flags": "مؤشرات الشبهة المرصودة",
        "clear_btn": "🗑️ إعادت ضبط ومسح الأدلة",
        "checksum_lbl": "📄 بصمة الدليل الرقمي وضمان النزاهة (SHA-256)",
        "trans_header": "🔠 كاشف ومترجم اللغات الجنائية الفوري",
        "trans_lbl": "اختر لغة ملف المحادثة الأصلي (Source Language):",
        "trans_btn": "🔮 ترجمة وتحديث مصفوفة التحليل الجنائي فوراً",
        "trans_back": "🔄 العودة للملف الأصلي (الغير مترجم)",
        "kw_inspector_title": "🔍 مستعرض تظليل أطراف المحادثة والكلمات المفتاحية",
        "load_archive_btn": "تحميل الأرشيف المستهدف",
        "archive_search_lbl": "استدعاء قضية مؤرشفة سابقة برقم الملف:",
        "stored_records_lbl": "🗄️ السجلات المركزية المخزنة حالياً:",
        "no_evidence_msg": "⚠️ الرجاء سحب وإسقاط ملف المحادثة (.txt / .json) أدناه للبدء بالفحص والتحليل الجنائي المتقدم.",
        "active_trans_msg": "📊 مصفوفة التحليل تعمل حالياً بناءً على [النص المترجم المعتمد].",
        "no_participants": "لم يتم استخراج أطراف مهيكلة للمحادثة.",
        "osint_header": "🔎 رصد المعرفات واستخبارات حسابات التواصل الاجتماعي",
        "osint_btn": "⚡ تشغيل فحص البصمة الرقمية على المنصات",
        "osint_custom_input": "أو أدخل معرفاً (Username) محدداً للمشتبه به للبحث عنه:",
        "col_platform": "منصة التواصل الاجتماعي",
        "col_profile": "رابط الحساب المرصود",
        "col_osint_status": "نتيجة التتبع والاستخبار",
        "parties_title": "👥 أطراف القضية المعرفة",
    },
}

# ==============================================================================
# MAIN STREAMLIT APPLICATION
# ==============================================================================
st.set_page_config(page_title="CFIS - Advanced Forensic Suite", layout="wide")
apply_custom_theme()

if "active_chat_content" not in st.session_state:
  st.session_state["active_chat_content"] = None
if "active_file_hash" not in st.session_state:
  st.session_state["active_file_hash"] = "NO_EVIDENCE_STREAM"
if "translated_chat_content" not in st.session_state:
  st.session_state["translated_chat_content"] = None
if "last_osint_results" not in st.session_state:
  st.session_state["last_osint_results"] = []
if "audit_trail" not in st.session_state:
  st.session_state["audit_trail"] = []


def add_audit_entry(phase, action, officer, file_hash):
  entry = {
      "phase": phase,
      "action": action,
      "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
      "officer": officer,
      "hash_stamp": file_hash,
  }
  st.session_state["audit_trail"].append(entry)


# Sidebar Clean Metadata
lang = st.sidebar.selectbox("🌐 UI Language / لغة الواجهة", ["العربية", "English"])
tx = LEXICON[lang]

st.sidebar.header(tx["sb_header"])
case_id = st.sidebar.text_input(tx["sb_case"], value="2026/CID/1054")
investigator = st.sidebar.text_input(tx["sb_officer"], value="Lt. Dana Khalifa")
suspect_name = st.sidebar.text_input(tx["sb_suspect"], value="Target_Alpha")
victim_name = st.sidebar.text_input(tx["sb_victim"], value="Victim_Bravo")

if st.sidebar.button(tx["clear_btn"]):
  st.session_state["active_chat_content"] = None
  st.session_state["active_file_hash"] = "NO_EVIDENCE_STREAM"
  st.session_state["translated_chat_content"] = None
  st.session_state["audit_trail"] = []
  st.rerun()

# Main Title Header
st.title(tx["title"])
st.subheader(tx["sub"])
st.markdown("<hr style='border-color: #30363d;'>", unsafe_allow_html=True)

# Main Body Controls Section (Restored Drag & Drop + Settings)
st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
col_top1, col_top2, col_top3 = st.columns([2, 1, 1])

with col_top1:
  uploaded_file = st.file_uploader(tx["upload_lbl"], type=["txt", "json"])

with col_top2:
  app_source = st.selectbox(
      tx["app_src_lbl"],
      ["WhatsApp (.txt)", "Telegram (.json)", "Instagram DMs (.json)", "Facebook Messenger (.json)"],
  )

with col_top3:
  device_role = st.selectbox(
      tx["dev_role_lbl"],
      ["🔴 Suspect / Criminal Device", "🔵 Victim Device"],
  )
st.markdown("</div>", unsafe_allow_html=True)

if uploaded_file is not None:
  file_bytes = uploaded_file.read()
  raw_content = parse_uploaded_chat(file_bytes, app_source)
  calculated_hash = hashlib.sha256(file_bytes).hexdigest()

  if st.session_state["active_file_hash"] != calculated_hash:
    st.session_state["active_chat_content"] = raw_content
    st.session_state["active_file_hash"] = calculated_hash
    st.session_state["translated_chat_content"] = None
    st.session_state["audit_trail"] = []
    add_audit_entry("Ingestion", "Evidence Uploaded & Parsed", investigator, calculated_hash)

working_text = (
    st.session_state["translated_chat_content"]
    if st.session_state["translated_chat_content"]
    else st.session_state["active_chat_content"]
)

if working_text:
  if st.session_state["translated_chat_content"]:
    st.info(tx["active_trans_msg"])

  st.markdown(f"**{tx['checksum_lbl']}:** `{st.session_state['active_file_hash']}`")

  threat_score, risk_label = analyze_chat_threat_score(working_text, lang, device_role)
  tone_metrics = analyze_sentiment_and_tone(working_text)
  extracted_amounts, total_money = extract_financial_amounts(working_text)

  # Identified Parties Bar
  st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
  st.markdown(f"#### {tx['parties_title']}")
  cp1, cp2, cp3 = st.columns(3)
  with cp1:
    st.markdown(f"🎯 **Suspect:** `{suspect_name}`")
  with cp2:
    st.markdown(f"🛡️ **Victim:** `{victim_name}`")
  with cp3:
    st.markdown(f"📋 **Case Ref:** `{case_id}`")
  st.markdown("</div>", unsafe_allow_html=True)

  # Intelligence Cards Matrix
  st.markdown("### " + tx["intel_header"])
  col_a, col_b, col_c = st.columns(3)

  with col_a:
    st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
    st.markdown(f"#### {tx['card_tone']}")
    fig_tone = px.pie(
        names=list(tone_metrics.keys()),
        values=list(tone_metrics.values()),
        color_discrete_sequence=["#ef4444", "#3b82f6", "#f59e0b"],
        hole=0.4,
    )
    fig_tone.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=200,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#c9d1d9"),
    )
    st.plotly_chart(fig_tone, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

  with col_b:
    st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
    st.markdown(f"#### {tx['card_financial']}")
    st.metric(
        label="Total Demanded / Mentioned",
        value=f"{total_money:,} BHD",
        delta=f"{len(extracted_amounts)} transaction instances",
    )
    st.write("Extracted raw values:", ", ".join(extracted_amounts) if extracted_amounts else "None")
    st.markdown("</div>", unsafe_allow_html=True)

  with col_c:
    st.markdown("<div class='forensic-card'>", unsafe_allow_html=True)
    st.markdown(f"#### {tx['card_speaker']}")
    contacts_map = extract_contacts_map(working_text)
    if contacts_map:
      for c_name, c_style in contacts_map.items():
        st.markdown(
            f"<span class='contact-badge' style='background-color: {c_style['bg']}; border-color: {c_style['border']}; color: {c_style['text']};'>{c_name}</span>",
            unsafe_allow_html=True,
        )
    else:
      st.write(tx["no_participants"])
    st.markdown("</div>", unsafe_allow_html=True)

  st.markdown(f"### {tx['threat_idx']} `{threat_score}/100` {tx['forensic_triage_res']} **{risk_label}**")

  ibans = list(set(re.findall(r"\b[A-Z]{2}\d{2}[A-Z0-9]{12,30}\b", working_text)))
  phones = list(set(re.findall(r"\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}", working_text)))
  emails = list(set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", working_text)))
  urls = list(set(re.findall(r"https?://[^\s]+|\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", working_text)))

  st.markdown("---")
  st.markdown("### " + tx["art_title"])
  t_bank, t_phone, t_url, t_social, t_vault = st.tabs([
      tx["tab_bank"],
      tx["tab_phone"],
      tx["tab_url"],
      tx["tab_social"],
      tx["tab_vault"],
  ])

  with t_bank:
    if ibans:
      iban_data = []
      for ib in ibans:
        match = check_cross_case(ib)
        iban_data.append({
            tx["col_iban"]: ib,
            tx["col_status"]: f"⚠️ Matched Case: {match[0]} (Officer: {match[1]})" if match else "CLEAR / NO MATCH",
        })
      st.dataframe(pd.DataFrame(iban_data), use_container_width=True)
    else:
      st.info("No IBAN accounts identified.")

  with t_phone:
    if phones or emails:
      comms_data = []
      for ph in phones:
        match = check_cross_case(ph)
        comms_data.append({"Indicator": ph, "Type": "Phone Number", tx["col_match"]: f"⚠️ Matched Case: {match[0]}" if match else "No Match"})
      for em in emails:
        match = check_cross_case(em)
        comms_data.append({"Indicator": em, "Type": "Email", tx["col_match"]: f"⚠️ Matched Case: {match[0]}" if match else "No Match"})
      st.dataframe(pd.DataFrame(comms_data), use_container_width=True)
    else:
      st.info("No telephony or email indicators identified.")

  with t_url:
    if urls:
      url_data = []
      for u in urls:
        r_label, r_score, r_flags = analyze_url_or_ip(u, lang)
        url_data.append({tx["col_url"]: u, tx["col_risk"]: r_label, tx["col_score"]: r_score, tx["col_flags"]: r_flags})
      st.dataframe(pd.DataFrame(url_data), use_container_width=True)
    else:
      st.info("No URLs or IP addresses extracted.")

  with t_social:
    st.markdown("#### " + tx["osint_header"])
    detected_handles = extract_usernames_and_handles(working_text)
    custom_handle = st.text_input(tx["osint_custom_input"])
    target_handles = detected_handles.copy()
    if custom_handle:
      target_handles.append(custom_handle.strip())

    st.write("Handles extracted for OSINT scan:", ", ".join(target_handles) if target_handles else "None")

    if st.button(tx["osint_btn"]):
      recon_results = []
      platforms = [
          ("Telegram", "https://t.me/{}"),
          ("Instagram", "https://www.instagram.com/{}/"),
          ("Twitter / X", "https://x.com/{}"),
          ("GitHub", "https://github.com/{}"),
      ]
      for handle in target_handles:
        clean_h = handle.replace("@", "")
        for p_name, p_url in platforms:
          endpoint = p_url.format(clean_h)
          status, profile_link = check_social_media_account(p_name, endpoint)
          recon_results.append({
              "Handle": clean_h,
              tx["col_platform"]: p_name,
              tx["col_osint_status"]: status,
              tx["col_profile"]: profile_link,
          })
      st.session_state["last_osint_results"] = recon_results
      add_audit_entry("OSINT", f"Recon performed on handles: {', '.join(target_handles)}", investigator, st.session_state["active_file_hash"])

    if st.session_state["last_osint_results"]:
      st.dataframe(pd.DataFrame(st.session_state["last_osint_results"]), use_container_width=True)

  with t_vault:
    st.markdown("#### " + tx["stored_records_lbl"])
    all_ind = get_all_indicators()
    st.dataframe(all_ind, use_container_width=True)

    archive_id_query = st.text_input(tx["archive_search_lbl"])
    if st.button(tx["load_archive_btn"]):
      archived_case = load_full_case(archive_id_query)
      if archived_case:
        st.session_state["active_chat_content"] = archived_case[0]
        st.session_state["active_file_hash"] = archived_case[4]
        st.success(f"Archived case {archive_id_query} loaded successfully!")
        st.rerun()
      else:
        st.error("Case ID not found in central archive.")

  # Keyword Inspector View
  st.markdown("---")
  st.markdown("### " + tx["kw_inspector_title"])
  rendered_html_chat = generate_keyword_highlight_html(working_text, contacts_map)
  st.markdown(f'<div class="highlight-box">{rendered_html_chat}</div>', unsafe_allow_html=True)

  # Forensic Translator
  st.markdown("---")
  st.markdown("### " + tx["trans_header"])
  col_tr1, col_tr2 = st.columns([2, 1])
  with col_tr1:
    src_lang = st.selectbox(tx["trans_lbl"], ["auto", "ar", "en", "fa", "ur", "ru", "zh-CN", "ja"])
  with col_tr2:
    if st.button(tx["trans_btn"]):
      try:
        translated = GoogleTranslator(source=src_lang, target="en").translate(working_text[:4000])
        st.session_state["translated_chat_content"] = translated
        add_audit_entry("Translation", f"Text translated from {src_lang} to EN", investigator, st.session_state["active_file_hash"])
        st.rerun()
      except Exception as e:
        st.error(f"Translation failed: {e}")

  if st.session_state["translated_chat_content"]:
    if st.button(tx["trans_back"]):
      st.session_state["translated_chat_content"] = None
      st.rerun()

  # Action Bar (Restored Vault Saving and PDF Generation to Main Dashboard Area)
  st.markdown("---")
  act_col1, act_col2 = st.columns(2)

  with act_col1:
    if st.button(tx["save_vault_btn"], use_container_width=True):
      success = save_full_case(
          case_id,
          investigator,
          suspect_name,
          victim_name,
          app_source,
          device_role,
          st.session_state["active_file_hash"],
          st.session_state["active_chat_content"],
      )
      if success:
        st.success("Case saved to local vault archive.")
        add_audit_entry("Archival", "Case Saved to Vault", investigator, st.session_state["active_file_hash"])
      else:
        st.error("Error saving case.")

  with act_col2:
    pdf_bytes = create_reportlab_pdf(
        case_id=case_id,
        officer=investigator,
        suspect=suspect_name,
        victim=victim_name,
        extracted_participants=list(contacts_map.keys()),
        app_src=app_source,
        dev_role=device_role,
        file_hash=st.session_state["active_file_hash"],
        score=threat_score,
        score_label=risk_label,
        tone_metrics=tone_metrics,
        ibans=ibans,
        emails=emails,
        phones=phones,
        urls=urls,
        total_money=total_money,
        recon_data=st.session_state["last_osint_results"],
        audit_logs=st.session_state["audit_trail"],
    )
    st.download_button(
        label=tx["pdf_btn"],
        data=pdf_bytes,
        file_name=f"Forensic_Report_{case_id.replace('/', '_')}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

else:
  st.warning(tx["no_evidence_msg"])

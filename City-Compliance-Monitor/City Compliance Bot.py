"""
City Compliance & Logistics Auditor (v1.0)
Generic version for Business Automation Portfolio.
Description: Automates the cross-referencing between official city traffic 
restrictions (PDF) and active worksites using Fuzzy Matching logic.
"""

import os
import re
import pandas as pd
import glob
from datetime import datetime
import smtplib
from email.message import EmailMessage
import unicodedata
import shutil
from fuzzywuzzy import fuzz
import pdfplumber

# ==============================
# ⚙️ GENERIC CONFIGURATION
# ==============================
# All paths are now relative to the script location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input_files")
OUTPUT_DIR = os.path.join(BASE_DIR, "reports")
LOG_FILE = os.path.join(OUTPUT_DIR, "process_log.txt")

# Create directories if they don't exist
for folder in [INPUT_DIR, OUTPUT_DIR]:
    os.makedirs(folder, exist_ok=True)

# File names (Placeholders)
CLIENTS_DB = os.path.join(INPUT_DIR, "active_worksites.xlsx")
MASTER_STREET_LIST = os.path.join(INPUT_DIR, "master_street_list.xlsx")

# Notification Settings (To be filled by user)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = "your-email@example.com"
SENDER_PASS = "your-app-password"
RECEIVER_EMAILS = ["manager@example.com"]

# Logic Settings
FUZZY_THRESHOLD = 80
# Keywords for balance calculation (Deposits add 1, Removals subtract 1)
KW_DEPOSIT = ["DEPOSIT", "DELIVERY", "INSTALLATION", "START"]
KW_REMOVAL = ["REMOVAL", "PICKUP", "END", "COLLECT"]

# ==============================
# 🔧 UTILS & LOGGING
# ==============================

def log_event(text):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    message = f"[{timestamp}] {text}"
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(message + "\n")
    print(message)

def normalize_text(text):
    if pd.isna(text) or not text: return ""
    text = str(text).upper().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

# ==============================
# 📋 DATA PROCESSING
# ==============================

def get_active_inventory_balance():
    """
    Reads local Excel and calculates current stock balance per site.
    Returns only sites with balance > 0.
    """
    try:
        log_event("📂 Loading inventory and calculating site balances...")
        df = pd.read_excel(CLIENTS_DB)
        inventory_register = {}

        for _, row in df.iterrows():
            # Generic column mapping
            address = str(row.get('Address', '')).upper()
            client = str(row.get('Client', '')).upper()
            service_type = str(row.get('Service_Type', '')).upper()

            if address and client:
                # Group by client and normalized street name
                street_key = (client, address)
                
                if street_key not in inventory_register:
                    inventory_register[street_key] = {'client': client, 'address': address, 'balance': 0}
                
                if any(kw in service_type for kw in KW_DEPOSIT):
                    inventory_register[street_key]['balance'] += 1
                elif any(kw in service_type for kw in KW_REMOVAL):
                    inventory_register[street_key]['balance'] -= 1

        active_sites = [v for k, v in inventory_register.items() if v['balance'] > 0]
        log_event(f"✅ Found {len(active_sites)} active sites to monitor.")
        return pd.DataFrame(active_sites)
    except Exception as e:
        log_event(f"❌ Error loading data: {e}")
        return pd.DataFrame()

# ==============================
# 🔍 FUZZY MATCHING ENGINE
# ==============================

def run_compliance_audit(df_sites, restricted_streets):
    log_event("🔍 Running Fuzzy Matching audit...")
    alerts = []
    
    for _, site in df_sites.iterrows():
        site_addr = normalize_text(site['address'])
        
        for restricted in restricted_streets:
            restricted_norm = normalize_text(restricted)
            
            # Fuzzy ratio calculation
            score = fuzz.token_sort_ratio(site_addr, restricted_norm)
            
            if score >= FUZZY_THRESHOLD:
                alerts.append({
                    'Client': site['client'],
                    'Site_Address': site['address'],
                    'Restricted_Area': restricted,
                    'Confidence': f"{score}%",
                    'Active_Assets': site['balance']
                })
                log_event(f"⚠️ MATCH FOUND: {site['client']} at {restricted} ({score}%)")
    return alerts

# ==============================
# 📧 NOTIFICATION SYSTEM
# ==============================

def send_alert_report(alerts):
    if not alerts:
        log_event("✅ No compliance risks found today.")
        return

    try:
        msg = EmailMessage()
        msg['Subject'] = f"🚨 Compliance Alert: City Traffic Restrictions - {datetime.now().strftime('%d/%m/%Y')}"
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(RECEIVER_EMAILS)

        content = "AUTOMATED COMPLIANCE REPORT\n" + "="*30 + "\n\n"
        for i, a in enumerate(alerts, 1):
            content += f"{i}. CLIENT: {a['Client']}\n"
            content += f"   📍 Site: {a['Site_Address']}\n"
            content += f"   🚫 Restriction: {a['Restricted_Area']} (Match: {a['Confidence']})\n"
            content += f"   📦 Active Assets: {a['Active_Assets']}\n"
            content += "-"*30 + "\n"

        msg.set_content(content)

        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASS)
            smtp.send_message(msg)
        log_event("📧 Alert report sent successfully.")
    except Exception as e:
        log_event(f"❌ Failed to send email: {e}")

# ==============================
# 🚀 MAIN EXECUTION
# ==============================

def main():
    log_event("🚀 Starting Business Automation Audit...")
    
    # 1. Load active inventory
    df_active_sites = get_active_inventory_balance()
    
    # 2. Mock list of restricted streets (In real scenario, this comes from PDF extraction)
    # This keeps the script demo-ready for recruiters
    restricted_areas = ["Main Street", "Avenue of Liberty", "Broadway 45"] 
    
    if not df_active_sites.empty:
        # 3. Cross-reference
        matches = run_compliance_audit(df_active_sites, restricted_areas)
        
        # 4. Notify
        if SENDER_EMAIL != "your-email@example.com":
            send_alert_report(matches)
        else:
            log_event("📢 Email skipped (Configuration needed).")
            
    log_event("✅ Process Finished.")

if __name__ == "__main__":
    main()
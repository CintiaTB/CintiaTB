"""
Revenue Recovery Engine - Asset Overstay Auditor (v1.0)
Generic version for Business Automation Portfolio.
Description: Audits asset stays (containers, machinery, etc.) to identify 
unbilled overstays and recover lost revenue through automated alerts.
"""

import pandas as pd
import os
import unicodedata
from datetime import datetime

# ==============================
# ⚙️ GENERIC CONFIGURATION
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "inventory_history.xlsx")
OUTPUT_REPORT = os.path.join(BASE_DIR, f"Overstay_Report_{datetime.now().strftime('%Y%m%d')}.xlsx")

# Business Logic Constants
DAYS_LIMIT_BILLING = 30    # Threshold for mandatory billing
DAYS_PRE_ALERTA = 25       # Threshold for commercial follow-up
VIP_CLIENTS = ["KEY_ACCOUNT_A", "GOVERNMENT_DEPT", "PARTNER_X"]

# ==============================
# 🛠️ ADDRESS & DATA CLEANING
# ==============================

def clean_address(address_raw):
    """Normalizes address to ensure accurate site grouping."""
    if pd.isna(address_raw): return "UNKNOWN_LOCATION"
    text = str(address_raw).upper().strip()
    # Normalize unicode (remove accents)
    clean_text = unicodedata.normalize("NFKD", text)
    clean_text = "".join(c for c in clean_text if not unicodedata.combining(c))
    return clean_text

def is_vip(client_name):
    return any(vip in str(client_name).upper() for vip in VIP_CLIENTS)

# ==============================
# 🧠 AUDIT & CALCULATION ENGINE
# ==============================

def run_overstay_audit():
    print("🚀 STARTING ASSET AUDIT...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: Input file '{INPUT_FILE}' not found.")
        return

    # Load data
    df = pd.read_excel(INPUT_FILE)
    
    try:
        df['Date'] = pd.to_datetime(df['Date'])
        # Sort by date and original index to maintain logical flow of movements
        df = df.sort_values(by=['Date']).reset_index()
    except Exception as e:
        print(f"❌ Date processing error: {e}")
        return

    sites = {}
    erp_discrepancies = []

    for _, row in df.iterrows():
        raw_addr = row.get('Address', 'Unknown')
        clean_addr = clean_address(raw_addr)
        client = str(row.get('Client', 'Generic Client')).strip().upper()
        concept = str(row.get('Movement_Type', '')).strip().upper()
        qty = row.get('Quantity', 0)
        current_date = row['Date']
        
        site_id = (client, clean_addr)
        
        if site_id not in sites:
            sites[site_id] = {
                'Balance': 0, 
                'Last_Movement': current_date,
                'Raw_Address': raw_addr,
                'Client': client
            }

        # --- LOGISTICS MATH LOGIC ---
        is_dep = any(kw in concept for kw in ["DEPOSIT", "DELIVERY", "START"])
        is_ret = any(kw in concept for kw in ["REMOVAL", "PICKUP", "END"])
        is_exchange = "EXCHANGE" in concept

        if is_exchange:
            # Exchanges refresh the "age" of the asset
            sites[site_id]['Last_Movement'] = current_date
        elif is_dep:
            sites[site_id]['Balance'] += 1
            sites[site_id]['Last_Movement'] = current_date
        elif is_ret:
            sites[site_id]['Balance'] -= 1
            # If assets still remain, we keep the original age of the oldest one
            if sites[site_id]['Balance'] <= 0:
                 sites[site_id]['Last_Movement'] = current_date

    # --- ALERT GENERATION ---
    alert_list = []
    today = datetime.now()

    for (client, addr), data in sites.items():
        balance = data['Balance']
        
        if balance > 0 and not is_vip(client):
            days_idle = (today - data['Last_Movement']).days
            
            status = ""
            if days_idle > DAYS_LIMIT_BILLING:
                status = "🔴 OVER LIMIT - BILL NOW"
            elif days_idle >= DAYS_PRE_ALERTA:
                status = "🟡 PRE-ALERT - FOLLOW UP"
                
            if status:
                alert_list.append({
                    'Status': status,
                    'Client': client,
                    'Address': data['Raw_Address'],
                    'Active_Assets': balance,
                    'Days_Idle': days_idle,
                    'Last_Activity': data['Last_Movement'].strftime('%d/%m/%Y')
                })

    # --- EXCEL REPORT GENERATION ---
    if alert_list:
        df_alerts = pd.DataFrame(alert_list).sort_values(by='Days_Idle', ascending=False)
        df_alerts.to_excel(OUTPUT_REPORT, index=False)
        print(f"✅ Audit complete. Report generated: {OUTPUT_REPORT}")
    else:
        print("✅ Audit complete. No overstays detected.")

if __name__ == "__main__":
    run_overstay_audit()
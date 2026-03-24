"""
Fleet & Staff Compliance Monitor (v1.0)
Generic version for Business Automation Portfolio.
Description: Merges expiration dates with staff contact info to automate 
proactive notifications via WhatsApp and Email summary.
"""

import pandas as pd
from datetime import datetime, timedelta
import os
import sys
import re

# ==============================
# ⚙️ GENERIC CONFIGURATION
# ==============================
# Detect execution path for portable .EXE usage
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(BASE_DIR)

# File Definitions (Generic naming)
EXPIRATION_DB = os.path.join(BASE_DIR, "expirations.xlsx") 
STAFF_VEHICLE_DB = os.path.join(BASE_DIR, "staff_contact_info.xlsx")         
HISTORY_LOG = os.path.join(BASE_DIR, "notification_history.xlsx")

# Notification Settings
MANAGER_EMAIL = "operations@example.com"
COUNTRY_PREFIX = "+34" 
TEST_MODE = True  # Set to False for real WhatsApp/Email sending

# ==============================
# 🔧 SUPPORT FUNCTIONS
# ==============================

def normalize_phone(phone):
    """Basic phone normalization for international format."""
    if pd.isna(phone): return None
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) == 9:
        return f"{COUNTRY_PREFIX}{digits}"
    return None

def log_event(text):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {text}")

# ==============================
# 🚀 MAIN AUDIT LOGIC
# ==============================

def run_compliance_check():
    log_event("🔍 Starting Compliance Audit...")
    
    if not os.path.exists(EXPIRATION_DB) or not os.path.exists(STAFF_VEHICLE_DB):
        log_event("❌ Error: Missing input Excel files.")
        return

    # 1. Load Data
    df_venc = pd.read_excel(EXPIRATION_DB, dtype=str)
    df_staff = pd.read_excel(STAFF_VEHICLE_DB, dtype=str)
    
    # 2. Merge logic (Generic columns)
    # Assumes common column 'Asset_ID' or 'Vehicle'
    df = pd.merge(df_venc, df_staff, on='Asset_ID', how='left')
    
    # 3. Date Filtering
    today = datetime.now().date()
    limit_date = today + timedelta(days=30)
    
    try:
        df["Expiry_Date"] = pd.to_datetime(df["Expiry_Date"], dayfirst=True, errors='coerce').dt.date
    except Exception as e:
        log_event(f"❌ Date processing error: {e}")
        return

    # Filter: Expired or expiring within 30 days
    pending = df[(df["Expiry_Date"] <= limit_date)].copy()
    
    log_event(f"📊 Items requiring attention: {len(pending)}")

    notifications = []
    for _, row in pending.iterrows():
        phone = normalize_phone(row.get("Phone"))
        expiry = row["Expiry_Date"]
        asset = row.get("Asset_ID", "Unknown")
        
        status = "🔴 EXPIRED" if expiry < today else "🟡 EXPIRING SOON"
        
        # Message construction
        msg = (
            f"Compliance Alert [{status}]\n"
            f"Item: {row.get('Document_Type', 'Document')}\n"
            f"Asset: {asset}\n"
            f"Expiry Date: {expiry.strftime('%d/%m/%Y')}\n"
        )
        
        notif_status = "Pending (Test Mode)"
        if not TEST_MODE and phone:
            # Here you would integrate pywhatkit or a WhatsApp API
            notif_status = "WhatsApp Sent"
        
        notifications.append({
            "Asset": asset,
            "Expiry": expiry,
            "Status": status,
            "Notification": notif_status,
            "Contact": row.get("Staff_Name", "N/A")
        })

    # 4. Export results
    if notifications:
        pd.DataFrame(notifications).to_excel(HISTORY_LOG, index=False)
        log_event(f"✅ Audit complete. History saved to {HISTORY_LOG}")

if __name__ == "__main__":
    run_compliance_check()
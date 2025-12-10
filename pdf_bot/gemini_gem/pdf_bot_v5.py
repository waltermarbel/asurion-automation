# -*- coding: utf-8 -*-
import requests
import json
import time
import os
import base64
from datetime import date
from supabase import create_client, Client
import logging

# --- CONFIGURATION ---
# Use os.environ.get in production
SUPABASE_URL = "YOUR_SUPABASE_URL_HERE"
SUPABASE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY_HERE"

PDFOTTER_TEMPLATE_ID = 'tem_XuwCXY2tEBLf7P'
PDFOTTER_API_KEY = 'test_8ej1qkRT55QPFCFUT58366JCuM8JDUmf' # Use ENV variable in prod
DRY_RUN = True # Safety Switch

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_signature_from_db(profile_id):
    """
    In the new system, Signatures should be stored in a 'profiles' table in Supabase.
    For now, we simulate fetching it.
    """
    # Placeholder: In production, query a 'profiles' table.
    # return supabase.table("profiles").select("signature_b64").eq("id", profile_id).execute()
    return "BASE64_STRING_HERE"

def generate_pdf_for_claim(claim):
    """
    Generates PDF using PDFOtter based on DB Claim Record.
    """
    claim_id = claim['claim_id']
    device = claim['devices'] # Joined data from Supabase

    logging.info(f"Processing Claim {claim_id} for {device.get('brand')} {device.get('model')}")

    # 1. Prepare Payload
    payload = {
        'data': {
            'Claim ID': str(claim_id),
            'Brand': device.get('brand'),
            'Model number': device.get('model'),
            'Serial number': device.get('serial_number'),
            'Purchase price': device.get('retail_price_estimate'),
            'Date of failure MM/DD/YYYY': claim.get('failure_date'),
            'Describe what happened': claim.get('failure_description'),
            # ... Add Account Holder details here ...
        }
    }

    # 2. DRY RUN Check
    if DRY_RUN:
        logging.info(f"[DRY RUN] Would generate PDF. Payload: {json.dumps(payload)}")

        # Simulate success for dry run
        supabase.table("claims").update({
            "status": "PDF_GENERATED_DRY_RUN",
        }).eq("claim_id", claim_id).execute()
        return True

    # 3. Call API
    api_url = f'https://www.pdfotter.com/api/v1/pdf_templates/{PDFOTTER_TEMPLATE_ID}/fill'
    try:
        response = requests.post(api_url, auth=(PDFOTTER_API_KEY, ''), json=payload)

        if response.status_code == 200:
            # 4. Save to Disk (Temporary) or Upload to Bucket
            filename = f"filled_{claim_id}.pdf"
            with open(filename, 'wb') as f:
                f.write(response.content)

            # 5. Update Database Status
            supabase.table("claims").update({
                "status": "PDF_GENERATED",
                "generated_pdf_url": filename # Ideally upload to Storage and put URL here
            }).eq("claim_id", claim_id).execute()

            logging.info("PDF Generated and DB updated.")
        else:
            logging.error(f"PDFOtter Failed: {response.text}")

    except Exception as e:
        logging.error(f"Error: {e}")

def main_loop():
    """
    Polls the DB for claims ready to file.
    """
    logging.info("Checking for pending claims...")

    # Select claims where status is 'SYSTEM_READY_TO_FILE'
    # Note: You need to set up Foreign Key joins in Supabase to fetch Device data automatically
    # This query assumes 'devices' table is referenced and joined
    try:
        response = supabase.table("claims").select("*, devices(*)").eq("status", "SYSTEM_READY_TO_FILE").execute()

        claims = response.data

        if not claims:
            logging.info("No claims pending generation.")
            return

        for claim in claims:
            generate_pdf_for_claim(claim)
            time.sleep(2)

    except Exception as e:
        logging.error(f"Error checking pending claims: {e}")

if __name__ == "__main__":
    main_loop()

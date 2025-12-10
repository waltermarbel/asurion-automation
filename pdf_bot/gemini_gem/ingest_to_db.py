import json
import os
from supabase import create_client, Client

# --- CONFIGURATION ---
# Replace with: os.environ.get("SUPABASE_URL") in production
SUPABASE_URL = "YOUR_SUPABASE_URL_HERE"
SUPABASE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY_HERE"
JSON_SOURCE_FILE = "../scanlily_sync_summary.json" # Output from your scraper (relative path)

# Initialize Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def ingest_inventory():
    print("--- Starting Ingestion to Supabase ---")

    # 1. Load the JSON data
    if not os.path.exists(JSON_SOURCE_FILE):
        print(f"Error: {JSON_SOURCE_FILE} not found. Make sure you run scanlily_sync_script.py first.")
        return

    with open(JSON_SOURCE_FILE, 'r') as f:
        raw_data = json.load(f)

    # 2. Iterate and Upsert to Database
    count = 0
    # Handle list or single object if the JSON structure varies, assuming list based on context
    if isinstance(raw_data, dict):
        raw_data = [raw_data] # Wrap in list if single object

    for item in raw_data:
        # Map your scraper fields to DB columns
        device_payload = {
            "scanlily_url": item.get("scanlily_url"),
            "brand": item.get("brand"),
            "model": item.get("model"),
            "serial_number": item.get("serial_number"),
            "category": item.get("category"),
            "status": "INGESTED"
        }

        # Upsert based on Serial Number or URL (Prevent duplicates)
        try:
            # Check if exists first (simplified logic)
            # In a real scenario, use upsert with a unique constraint on scanlily_url or serial_number
            existing = supabase.table("devices").select("*").eq("scanlily_url", device_payload["scanlily_url"]).execute()

            if not existing.data:
                response = supabase.table("devices").insert(device_payload).execute()
                print(f"Ingested: {device_payload.get('brand')} {device_payload.get('model')}")
                count += 1
            else:
                print(f"Skipping duplicate: {device_payload.get('scanlily_url')}")

        except Exception as e:
            print(f"Error ingesting item: {e}")

    print(f"--- Ingestion Complete. Added {count} new devices. ---")

if __name__ == "__main__":
    ingest_inventory()

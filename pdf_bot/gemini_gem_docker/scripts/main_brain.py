import time
import json
import os
import random
import requests
import schedule
import re
from datetime import date, datetime
from duckduckgo_search import DDGS
from psycopg2.extras import RealDictCursor
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

from db_utils import get_connection, log_system_event

# --- CONFIGURATION ---
PDFOTTER_TEMPLATE_ID = os.getenv("PDFOTTER_TEMPLATE_ID", "tem_XuwCXY2tEBLf7P")
PDFOTTER_API_KEY = os.getenv("PDFOTTER_API_KEY", "")
DRY_RUN = os.getenv("DRY_RUN", "False").lower() == "true"

INGEST_DIR = os.getenv("INGEST_DIR", "/app/data/ingest")
PDF_OUTPUT_DIR = os.getenv("PDF_OUTPUT_DIR", "/app/data/pdfs")
SIGNATURE_FILE = os.getenv("SIGNATURE_FILE", "/app/signatures/PC.txt")

HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8000"))

# Health metrics (simple timestamps)
last_ingest_ts = None
last_valuation_ts = None
last_claim_ts = None

# ==========================================
# MODULE 1: INGESTION ENGINE
# ==========================================
def ingest_files():
    global last_ingest_ts

    if not os.path.exists(INGEST_DIR):
        return

    for filename in os.listdir(INGEST_DIR):
        if not filename.endswith(".json") or filename.endswith(".processed"):
            continue

        filepath = os.path.join(INGEST_DIR, filename)
        print(f"[Ingest] Processing {filename}...")

        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            items = data if isinstance(data, list) else [data]

            conn = get_connection()
            if not conn:
                return

            new_count = 0
            try:
                with conn.cursor() as cur:
                    for item in items:
                        brand = item.get("brand") or item.get("Brand")
                        model = (
                            item.get("model")
                            or item.get("Model")
                            or item.get("model_number")
                        )
                        serial = item.get("serial_number") or item.get("Serial Number")
                        category = item.get("category") or item.get("Category")
                        url = item.get("scanlily_url", "N/A")

                        if not serial:
                            continue

                        cur.execute(
                            """
                            INSERT INTO devices (brand, model, serial_number, category, scanlily_url, status)
                            VALUES (%s, %s, %s, %s, %s, 'INGESTED')
                            ON CONFLICT (serial_number) DO NOTHING
                            """,
                            (brand, model, serial, category, url),
                        )
                        if cur.rowcount > 0:
                            new_count += 1

                conn.commit()
            finally:
                conn.close()

            os.rename(filepath, filepath + ".processed")
            log_system_event(
                "INGEST_BOT",
                "FILE_PROCESSED",
                {"filename": filename, "new_devices": new_count},
            )
            last_ingest_ts = datetime.utcnow()
            print(f"[Ingest] Success. Added {new_count} new devices.")

        except Exception as e:
            print(f"[Ingest Error] Failed to process {filename}: {e}")

# ==========================================
# MODULE 2: VALUATION ENGINE
# ==========================================
def run_valuation():
    global last_valuation_ts

    conn = get_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT device_id, brand, model
                FROM devices
                WHERE retail_price_estimate IS NULL
                  AND status = 'INGESTED'
                LIMIT 1
                """
            )
            device = cur.fetchone()

        if not device:
            return

        d_id, brand, model = device

        if not brand or not model:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE devices SET status = 'MANUAL_REVIEW' WHERE device_id = %s",
                    (d_id,),
                )
            conn.commit()
            print(f"[Valuation] Missing brand/model for {d_id}. Marked MANUAL_REVIEW.")
            return

        query = f"{brand} {model} price"
        print(f"[Valuation] Searching for: {query}...")

        time.sleep(random.uniform(3, 6))

        price = None
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=1))
                if results:
                    body = results[0].get("body", "")
                    match = re.search(r"\$[\d,]+(?:\.\d{2})?", body)
                    if match:
                        price_str = match.group(0).replace("$", "").replace(",", "")
                        price = float(price_str)
        except Exception as e:
            print(f"[Search Error] {e}")

        if price is not None:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE devices
                    SET retail_price_estimate = %s,
                        status = 'VALUATED'
                    WHERE device_id = %s
                    """,
                    (price, d_id),
                )
            conn.commit()
            log_system_event(
                "VALUATION_BOT",
                "PRICE_FOUND",
                {"device_id": str(d_id), "price": price},
            )
            last_valuation_ts = datetime.utcnow()
            print(f"[Valuation] Success. Set price to ${price:.2f}")
        else:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE devices SET status = 'MANUAL_REVIEW' WHERE device_id = %s",
                    (d_id,),
                )
            conn.commit()
            print(f"[Valuation] Price not found for {d_id}. Marked MANUAL_REVIEW.")

    finally:
        conn.close()

# ==========================================
# MODULE 3: CLAIM EXECUTION ENGINE
# ==========================================
def process_claims():
    global last_claim_ts

    conn = get_connection()
    if not conn:
        return

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT *
                FROM devices
                WHERE status = 'VALUATED'
                  AND device_id NOT IN (SELECT device_id FROM claims)
                LIMIT 1
                """
            )
            device = cur.fetchone()

        if not device:
            return

        print(f"[Claim] Generating PDF for {device['brand']} {device['model']}...")

        sig_data = "Signature on File"
        try:
            with open(SIGNATURE_FILE, "r") as f:
                sig_data = f.read().strip()
        except FileNotFoundError:
            print("[Claim] Signature file not found. Using text fallback.")

        payload = {
            "data": {
                "Brand": device["brand"],
                "Model number": device["model"],
                "Serial number": device["serial_number"],
                "Purchase price": float(device["retail_price_estimate"]),
                "Date of failure MM/DD/YYYY": date.today().strftime("%m/%d/%Y"),
                "Describe what happened": (
                    "Device stopped functioning during normal usage. "
                    "Screen does not power on."
                ),
                "Claim ID": str(device["device_id"]),
                "Signature of enrolled account holder": sig_data,
                "Date MM/DD/YYYY": date.today().strftime("%m/%d/%Y"),
            }
        }

        if DRY_RUN:
            print(
                f"[Dry Run] Simulated claim for {device['serial_number']}. "
                f"Value=${device['retail_price_estimate']}"
            )
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO claims (device_id, status, payout_estimate, failure_description)
                    VALUES (%s, 'DRY_RUN_COMPLETE', %s, 'Dry run test')
                    """,
                    (device["device_id"], device["retail_price_estimate"]),
                )
            conn.commit()
            last_claim_ts = datetime.utcnow()
            return

        if not PDFOTTER_API_KEY:
            print("[Claim Error] PDFOTTER_API_KEY not set.")
            return

        try:
            api_url = (
                f"https://www.pdfotter.com/api/v1/pdf_templates/"
                f"{PDFOTTER_TEMPLATE_ID}/fill"
            )
            resp = requests.post(
                api_url,
                auth=(PDFOTTER_API_KEY, ""),
                json=payload,
                timeout=60,
            )

            if resp.status_code == 200:
                os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)
                filename = f"claim_{device['serial_number']}.pdf"
                filepath = os.path.join(PDF_OUTPUT_DIR, filename)

                with open(filepath, "wb") as f:
                    f.write(resp.content)

                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO claims (device_id, status, generated_pdf_filename, payout_estimate)
                        VALUES (%s, 'PDF_GENERATED', %s, %s)
                        """,
                        (device["device_id"], filename, device["retail_price_estimate"]),
                    )
                conn.commit()

                log_system_event("CLAIM_BOT", "PDF_GENERATED", {"filename": filename})
                last_claim_ts = datetime.utcnow()
                print(f"[Claim] Success. PDF saved to {filepath}")
            else:
                print(f"[Claim Error] PDFOtter API: {resp.status_code} {resp.text}")

        except Exception as e:
            print(f"[Claim Error] Request failed: {e}")

    finally:
        conn.close()

# ==========================================
# HEALTH SERVER
# ==========================================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/healthz":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

        body = {
            "status": "ok",
            "dry_run": DRY_RUN,
            "last_ingest_ts": last_ingest_ts.isoformat() if last_ingest_ts else None,
            "last_valuation_ts": last_valuation_ts.isoformat() if last_valuation_ts else None,
            "last_claim_ts": last_claim_ts.isoformat() if last_claim_ts else None,
        }
        self.wfile.write(json.dumps(body).encode("utf-8"))

def start_health_server():
    server = HTTPServer(("0.0.0.0", HEALTH_PORT), HealthHandler)
    print(f"[Health] HTTP health server listening on 0.0.0.0:{HEALTH_PORT}")
    server.serve_forever()

# ==========================================
# MAIN LOOP
# ==========================================
def main():
    print("--- Gemini Gem Engine Initialized (v5.3) ---")
    print(f"--- Configuration: DRY_RUN={DRY_RUN} ---")

    # Start health server in background thread
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()

    schedule.every(10).seconds.do(ingest_files)
    schedule.every(30).seconds.do(run_valuation)
    schedule.every(60).seconds.do(process_claims)

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()

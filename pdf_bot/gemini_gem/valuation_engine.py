import time
import random
from duckduckgo_search import DDGS
from supabase import create_client, Client
import logging

# --- CONFIG ---
# Replace with: os.environ.get("SUPABASE_URL") in production
SUPABASE_URL = "YOUR_SUPABASE_URL_HERE"
SUPABASE_KEY = "YOUR_SUPABASE_SERVICE_ROLE_KEY_HERE"

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

logging.basicConfig(level=logging.INFO)

def get_market_price(brand, model):
    """Searches DDG for price."""
    query = f"{brand} {model} price"
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=1))
            if results:
                # Basic logic to find a price in the snippet
                # (You can enhance this with the regex from pdf_bot.py)
                import re
                snippet = results[0].get('body', '')
                match = re.search(r"\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", snippet)
                if match:
                    price_str = match.group(1).replace(',', '')
                    return float(price_str)
    except Exception as e:
        logging.error(f"Search failed: {e}")
    return None

def run_valuation_loop():
    logging.info("--- Starting Valuation Engine ---")

    # 1. Fetch devices needing valuation
    response = supabase.table("devices").select("*").is_("retail_price_estimate", "null").execute()
    devices = response.data

    if not devices:
        logging.info("No devices need valuation.")
        return

    for device in devices:
        brand = device.get('brand')
        model = device.get('model')

        if brand and model:
            logging.info(f"Valuating: {brand} {model}")
            price = get_market_price(brand, model)

            if price:
                # 2. Update Database
                supabase.table("devices").update({
                    "retail_price_estimate": price,
                    "status": "VALUATED"
                }).eq("device_id", device['device_id']).execute()

                # 3. Log it
                supabase.table("system_log").insert({
                    "actor": "VALUATION_ENGINE",
                    "action": "PRICE_UPDATE",
                    "details": {"device_id": device['device_id'], "price": price}
                }).execute()
                logging.info(f"Updated price: ${price}")
            else:
                 logging.warning("Could not find price.")

            # Rate Limit
            time.sleep(random.uniform(2, 5))

if __name__ == "__main__":
    run_valuation_loop()

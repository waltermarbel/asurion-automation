# 💎 Gemini Gem v5.2: System Manual & Operator's Guide

**Version:** 5.2 (Master Blueprint)
**Architecture:** Dockerized Microservices (Python + PostgreSQL)

---

## 1. Executive Summary

**Gemini Gem** is an industrial-grade automation platform designed for **Liquidation Arbitrage**. Its primary mission is to autonomously process high-volume electronics inventory to identify, valuate, and execute insurance claims.

**The "Magic" Loop:**

1.  **Ingest**: You dump raw inventory lists (JSON) into a folder.
2.  **Valuate**: The system searches the web to find the retail price of every item.
3.  **Execute**: The system automatically generates filled, signed PDF claim forms for high-value items.
4.  **Audit**: Every action is logged in a tamper-proof SQL database.

---

## 2. System Architecture

The system runs on **Oracle Cloud Linux** using **Docker Containers**. It consists of two main "Services" that run 24/7.

### A. The Vault (Database)

- **Technology**: PostgreSQL 15
- **Role**: The "Single Source of Truth." It replaces fragile text files. All data—policies, devices, claims, and logs—live here.
- **Persistence**: Data is stored in `postgres_data/`, so it survives server restarts.

### B. The Brain (Automation Engine)

- **Technology**: Python 3.9 Container
- **Role**: A continuous background worker running `scripts/main_brain.py`.
- **Mechanism**: uses the `schedule` library to run three distinct modules in an infinite loop.

---

## 3. Deep Dive: Component Breakdown

### 📁 File Structure

```text
gemini_gem_docker/
├── docker-compose.yml       # The "Conductor" (launches everything)
├── init.sql                 # The "Blueprints" (database tables)
├── requirements.txt         # The "Tools" (python libraries)
├── scripts/
│   ├── main_brain.py        # The "Logic" (the actual bot)
│   └── db_utils.py          # The "Connector" (database helper)
├── data/
│   ├── ingest/              # INPUT: Drop your JSON files here
│   └── pdfs/                # OUTPUT: Collect your PDF claims here
└── signatures/
    └── PC.txt               # CONFIG: Your Base64 signature string
```

### 🧠 The Brain (`scripts/main_brain.py`)

This is the heart of the system. It runs three specific engines in parallel:

#### **Module 1: Ingestion Engine**

- **What it does**: Watches `/app/data/ingest` for new `.json` files.
- **Logic**:
  1.  Reads the file.
  2.  Extracts Brand, Model, Serial Number.
  3.  **Upserts** into the `devices` table. (It ignores duplicates based on Serial Number).
  4.  Renames the file to `.processed` so it isn't read twice.
- **Status Change**: Sets device status to `'INGESTED'`.

#### **Module 2: Valuation Engine**

- **What it does**: Finds items that exist but have no price.
- **Logic**:
  1.  Queries DB: `SELECT * FROM devices WHERE price IS NULL`.
  2.  Uses **DuckDuckGo** to search for `"{Brand} {Model} price"`.
  3.  Uses Regex to find the first cash value (e.g., `$299.99`) in the search results.
  4.  Updates the Database with the price.
- **Status Change**: Sets device status to `'VALUATED'`.

#### **Module 3: Claim Execution Engine**

- **What it does**: Finds valuable items and generates the paperwork.
- **Logic**:
  1.  Queries DB: `SELECT * FROM devices WHERE status='VALUATED'`.
  2.  Reads your signature from `signatures/PC.txt`.
  3.  Sends a payload to the **PDFOtter API** (or simulates if DRY_RUN=True).
  4.  Saves the resulting PDF to `/app/data/pdfs/`.
- **Status Change**: Creates a record in `claims` table and sets status to `'PDF_GENERATED'`.

---

## 4. Deep Dive: The Database (`init.sql`)

The system uses 5 key tables:

1.  **`policies`**: Defines who we claim against (Asurion, Verizon, etc.).
2.  **`policy_rules`**: Logic for deductibles (e.g., "Laptops have $99 deductible").
3.  **`devices`**: The master inventory ledger.
    - _Columns_: Brand, Model, Serial, Retail Price, Status.
4.  **`claims`**: The history of what we filed.
    - _Columns_: Claim ID, Failure Date, Payout Estimate, PDF Filename.
5.  **`system_log`**: An immutable audit trail.
    - _Example_: `actor='VALUATION_BOT'`, `action='PRICE_FOUND'`, `details='{"price": 450.00}'`.

---

## 5. Operational Guide

### How to Deploy

1.  **Upload**: Copy `gemini_gem_docker` to your VM.
2.  **Start**: Run `docker-compose up -d --build`.
3.  **Stop**: Run `docker-compose down`.

### How to Feed the Machine

Create a JSON file (e.g., `batch_001.json`) on your laptop:

```json
[
  {
    "brand": "Samsung",
    "model": "Galaxy S23",
    "serial_number": "R5C...A",
    "category": "Smartphone"
  }
]
```

Upload it to the ingest folder:
`scp batch_001.json user@vm:~/gemini_gem_docker/data/ingest/`

### How to Get Results

Download your PDFs:
`scp user@vm:~/gemini_gem_docker/data/pdfs/*.pdf ./my_local_folder/`

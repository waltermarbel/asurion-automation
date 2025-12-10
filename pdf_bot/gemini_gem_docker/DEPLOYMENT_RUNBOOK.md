# Gemini Gem v5.3 Deployment Runbook

Here is the compressed runbook to go from zero → live.

## 1. One-Shot Setup on the VM

SSH into the VM and run:

```bash
# OS + Docker + workspace
sudo dnf update -y
sudo dnf install -y dnf-utils zip unzip git nano curl
sudo dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io
sudo systemctl enable --now docker
sudo usermod -aG docker $USER

mkdir -p ~/gemini_gem/{data/ingest,data/pdfs,signatures,scripts,postgres_data,docs}
cd ~/gemini_gem
```

## 2. Drop in Files (summary)

You should transfer the `gemini_gem_docker` content to `~/gemini_gem` on the VM.
Ensuring the following structure:

- `init.sql`
- `.env`
- `Dockerfile`
- `docker-compose.yml`
- `scripts/requirements.txt`
- `scripts/db_utils.py`
- `scripts/main_brain.py`
- `signatures/PC.txt` (Your Base64 signature)

## 3. Build + Start

```bash
cd ~/gemini_gem
docker-compose down
docker-compose up -d --build
```

Check containers:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

You want both `db` and `gem_brain` to be healthy.

## 4. Health & Logs

Health endpoint (from your laptop/VM):

```bash
curl http://localhost:8000/healthz
```

Tail worker logs:

```bash
cd ~/gemini_gem
docker-compose logs -f gem_brain
```

You should see [Ingest], [Valuation], [Claim] as it cycles.

## 5. Feed One Test Device

1. Create `inventory.json` on your laptop:

```json
[
  {
    "brand": "Sony",
    "model": "WH-1000XM5",
    "serial_number": "SN123456789",
    "category": "Headphones",
    "scanlily_url": "http://example.com"
  }
]
```

2. Upload:

```bash
scp -i your-key.key inventory.json ubuntu@<VM_IP>:/home/ubuntu/gemini_gem/data/ingest/
```

3. Watch logs until:

   - `[Ingest] Processing inventory.json...`
   - `[Valuation] Success. Set price to ...`
   - `[Claim] Success. PDF saved to /app/data/pdfs/...`

4. Pull PDFs back:

```bash
mkdir -p ./my_claims
scp -i your-key.key ubuntu@<VM_IP>:/home/ubuntu/gemini_gem/data/pdfs/*.pdf ./my_claims/
```

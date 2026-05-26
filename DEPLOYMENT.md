# 🚀 Deployment Guide — AI Compliance Monitoring System

This document covers everything needed to deploy, run, and maintain the containerized AI Compliance Monitoring System from scratch.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start (Local Development)](#quick-start-local-development)
3. [Docker Secret Setup (API Key)](#docker-secret-setup-api-key)
4. [Running with Docker Compose](#running-with-docker-compose)
5. [Health Monitoring](#health-monitoring)
6. [Persistent Data Volumes](#persistent-data-volumes)
7. [CI/CD Pipeline (GitHub Actions)](#cicd-pipeline-github-actions)
8. [Pulling & Running the Published Image](#pulling--running-the-published-image)
9. [Environment Variables Reference](#environment-variables-reference)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Docker Desktop | ≥ 24.x | https://www.docker.com/products/docker-desktop |
| Docker Compose | ≥ 2.x (bundled with Desktop) | Bundled |
| Git | Any | https://git-scm.com |

Verify your installation:
```bash
docker --version
docker compose version
```

---

## Quick Start (Local Development)

```bash
# 1. Clone the repository
git clone https://github.com/Paragiscool/Compliance-Monitoring-System.git
cd Compliance-Monitoring-System

# 2. Create the Docker secret file (see section below)
echo -n "YOUR_GEMINI_API_KEY_HERE" > gemini_api_key.txt

# 3. Build and start in detached (background) mode
docker compose up --build -d

# 4. Open the dashboard
# Navigate to: http://localhost:8501
```

> **First build** takes 3–5 minutes to download the base image and install packages.  
> Subsequent starts are near-instant since Docker caches layers.

---

## Docker Secret Setup (API Key)

Instead of storing your API key in a `.env` file (which risks accidental commits), this project uses **Docker Secrets** — the key is stored in a local file that is never sent to the image and is excluded from Git.

### Step 1 — Create the secret file
```bash
# Windows (PowerShell)
"YOUR_GEMINI_API_KEY_HERE" | Out-File -FilePath gemini_api_key.txt -NoNewline -Encoding ascii

# macOS / Linux
echo -n "YOUR_GEMINI_API_KEY_HERE" > gemini_api_key.txt
```

> ⚠️ **Critical**: Do NOT add quotes, spaces, or newlines — just the raw key string.  
> The file is listed in `.gitignore` and `.dockerignore` and will never be committed.

### Step 2 — Read the secret in your app

The container exposes the key at `/run/secrets/gemini_api_key`. Your application reads it via the `GEMINI_API_KEY_FILE` environment variable. The relevant code pattern:

```python
import os

def get_api_key() -> str:
    """Read Gemini API key from Docker secret file, with .env fallback for local dev."""
    secret_file = os.getenv("GEMINI_API_KEY_FILE")
    if secret_file and os.path.exists(secret_file):
        with open(secret_file, "r") as f:
            return f.read().strip()
    # Fallback: standard env var (for local dev without Docker)
    return os.getenv("GEMINI_API_KEY", "")
```

---

## Running with Docker Compose

```bash
# Start (build if needed)
docker compose up --build -d

# Start without rebuilding
docker compose up -d

# Stop the container (data is preserved in volumes)
docker compose down

# Stop AND delete all persistent volumes (⚠️ WIPES MEMORY)
docker compose down -v

# Restart
docker compose restart
```

---

## Health Monitoring

The container exposes Streamlit's built-in `/_stcore/health` endpoint. Docker polls it every 30 seconds.

```bash
# Check container health status
docker inspect --format='{{.State.Health.Status}}' ai-compliance-monitor

# Stream live logs
docker compose logs -f

# View last 50 log lines
docker compose logs --tail=50

# See all running containers and their health
docker ps
```

Health states: `starting` → `healthy` ✅ or `unhealthy` ❌ (triggers auto-restart after 3 failures).

---

## Persistent Data Volumes

The following local directories/files are **bind-mounted** into the container. Data written inside the container is immediately reflected on your local machine and survives container restarts.

| Local Path | Container Path | Contents |
|---|---|---|
| `./checkpoints.sqlite` | `/app/checkpoints.sqlite` | LangGraph case memory & agent checkpoints |
| `./chroma_db/` | `/app/chroma_db/` | ChromaDB vectorstore (adaptive learning, false positives) |

> **Before first run**: Ensure `checkpoints.sqlite` and `chroma_db/` exist in your project root (generated during prior development sessions). If missing, the container will create empty ones.

### Backup your data
```bash
# Backup SQLite
cp checkpoints.sqlite checkpoints.sqlite.backup

# Backup ChromaDB
cp -r chroma_db/ chroma_db_backup/
```

---

## CI/CD Pipeline (GitHub Actions)

The pipeline is defined in [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml).

### What it does

| Trigger | Action |
|---|---|
| Push to `main` branch | Build + push image tagged `latest` and `sha-<hash>` |
| Push a version tag `v1.2.3` | Build + push image tagged `1.2.3` and `1.2` |
| Pull Request to `main` | Build only (validate, no push) |

### Where images are published
Images are pushed to **GitHub Container Registry (ghcr.io)**:
```
ghcr.io/paragiscool/compliance-monitoring-system:latest
ghcr.io/paragiscool/compliance-monitoring-system:v1.0.0
```

No external accounts needed — uses your repository's built-in `GITHUB_TOKEN`.

### Making the image publicly accessible
1. Go to your GitHub profile → **Packages**
2. Click the `compliance-monitoring-system` package
3. Package settings → Change visibility to **Public**

---

## Pulling & Running the Published Image

Once the CI/CD pipeline has published an image, teammates can run it without building locally:

```bash
# Pull the latest image
docker pull ghcr.io/paragiscool/compliance-monitoring-system:latest

# Run it (with your local volumes and secret)
docker run -d \
  --name ai-compliance-monitor \
  -p 8501:8501 \
  -v $(pwd)/checkpoints.sqlite:/app/checkpoints.sqlite \
  -v $(pwd)/chroma_db:/app/chroma_db \
  --secret gemini_api_key \
  -e PYTHONUNBUFFERED=1 \
  ghcr.io/paragiscool/compliance-monitoring-system:latest
```

Or use `docker-compose.yml` with the pre-built image by replacing `build: .` with:
```yaml
image: ghcr.io/paragiscool/compliance-monitoring-system:latest
```

---

## Environment Variables Reference

| Variable | Source | Description |
|---|---|---|
| `GEMINI_API_KEY_FILE` | Set by compose | Path to the Docker secret file containing the Gemini API key |
| `PYTHONUNBUFFERED` | Set by compose | `1` — ensures logs stream in real-time without buffering |

---

## Troubleshooting

### Docker daemon not running
```
error during connect: ... open //./pipe/docker_engine: The system cannot find the file specified
```
**Fix**: Open **Docker Desktop** and wait for the whale icon in the system tray to show "running".

---

### Port 8501 already in use
```
Error: bind: address already in use
```
**Fix**: Kill the existing process or change the host port in `docker-compose.yml`:
```yaml
ports:
  - "8502:8501"   # Use 8502 on your machine instead
```

---

### Container exits immediately / unhealthy
```bash
# Inspect logs for the crash reason
docker compose logs compliance-system

# Check the secret file exists and has content
cat gemini_api_key.txt
```

---

### ChromaDB or SQLite permissions error
The container runs as `appuser` (non-root). If volume files were created as root, fix ownership:
```bash
# Linux/macOS only
sudo chown -R 1000:1000 ./chroma_db ./checkpoints.sqlite
```

---

### Rebuilding from scratch
```bash
# Remove container, image, and rebuild completely
docker compose down
docker rmi project1b-compliancemonitoringsystem-compliance-system
docker compose up --build -d
```

---

*Last updated: May 2026 | Maintained by the Compliance AI Team*

<div align="center">

# 🤖 ChatOps AI — DevOps Assistant

**Kontrol infrastruktur kamu langsung dari Slack menggunakan bahasa natural**

[![CI](https://github.com/moran2-cyber/chatops-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/moran2-cyber/chatops-ai/actions)
[![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-purple)](https://langchain-ai.github.io/langgraph/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE) 

<!-- Demo GIF — rekam dengan screentogif.com lalu upload ke repo -->
![Demo ChatOps AI](docs/demo.gif)

</div>

---

## ✨ Fitur Utama

| Fitur | Deskripsi |
|---|---|
| 🧠 **Natural Language** | Ketik perintah bebas — AI yang parse maksudnya |
| 🐳 **Docker Control** | Deploy, restart, scale, rollback container |
| 🌐 **Porto-moran Integration** | Kontrol production portfolio langsung dari Slack |
| 🚀 **GitHub Actions Trigger** | Deploy ke production via chat tanpa SSH |
| 💓 **Health Check** | Ping endpoint Cloudflare untuk cek website live |
| 📋 **Audit Log** | Semua perintah tercatat di SQLite |
| 🔌 **Socket Mode** | Tidak perlu public URL — jalan di balik firewall |

---

## 🏗️ Arsitektur

```
Slack ──→ slack_handler.py ──→ ai/orchestrator.py (LangGraph + Groq)
                                      │
                    ┌─────────────────┼──────────────────┐
                    ▼                 ▼                  ▼
             Docker SDK        GitHub API         Cloudflare URL
           (lokal/staging)   (trigger CI/CD)    (health check prod)
```

**3 Lapisan:**
- **Pelayan** (`bot/`) — terima & kirim pesan Slack
- **Koki** (`ai/orchestrator.py`) — AI brain, pilih tool yang tepat
- **Bahan** (`ai/tools/`) — eksekusi aksi nyata ke infrastruktur

---

## 🚀 Quick Start

### Prasyarat
- Python 3.11+
- Docker Desktop
- Slack Workspace + App ([panduan setup](docs/slack-setup.md))
- Groq API Key (gratis di [console.groq.com](https://console.groq.com))

### Instalasi

```bash
# 1. Clone repo
git clone https://github.com/moran2-cyber/chatops-ai
cd chatops-ai

# 2. Setup environment
cp .env.example .env
# Edit .env — isi semua token

# 3. Jalankan dengan Docker
docker compose up -d

# Atau jalankan langsung
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Konfigurasi `.env`

```env
SLACK_BOT_TOKEN=xoxb-...        # dari OAuth & Permissions
SLACK_APP_TOKEN=xapp-...        # dari Socket Mode
SLACK_SIGNING_SECRET=...        # dari Basic Information
GROQ_API_KEY=gsk_...            # dari console.groq.com
GITHUB_TOKEN=ghp_...            # dari github.com/settings/tokens
```

---

## 💬 Contoh Perintah

Bot memahami bahasa natural — tidak perlu format kaku:

```
# Status & Monitoring
@DevOps Bot cek semua container masih hidup ga?
@DevOps Bot status porto-moran
@DevOps Bot website production bisa diakses?

# Logs
@DevOps Bot liat log error backend terbaru 50 baris
@DevOps Bot ada error apa di porto-moran api?

# Deploy & CI/CD
@DevOps Bot deploy porto-moran ke production
@DevOps Bot cek status workflow CI/CD terbaru
@DevOps Bot deploy selesai belum?

# Container Management
@DevOps Bot restart frontend porto-moran
@DevOps Bot scale worker jadi 3 instance
```

---

## 📁 Struktur Proyek

```
chatops-ai/
├── main.py                      # Entry point
├── bot/
│   └── slack_handler.py         # Slack event handler & Block Kit formatter
├── ai/
│   ├── orchestrator.py          # LangGraph ReAct agent
│   └── tools/
│       ├── health_tool.py       # Cek status Docker container
│       ├── log_tool.py          # Baca log container
│       ├── docker_tool.py       # Deploy, restart, rollback
│       ├── scale_tool.py        # Scale replika
│       ├── portomoran_tool.py   # Tools khusus porto-moran
│       ├── github_tool.py       # Trigger GitHub Actions
│       └── healthcheck_tool.py  # Ping URL production
├── .github/workflows/
│   └── ci.yml                   # Lint + Docker build check
├── docker-compose.yml
├── Dockerfile
└── .env.example
```

---

## 🛠️ Tech Stack

- **[Slack Bolt](https://slack.dev/bolt-python/)** — Slack app framework
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** — AI agent orchestration
- **[Groq](https://console.groq.com)** — LLM inference (llama-3.3-70b-versatile)
- **[Docker SDK](https://docker-py.readthedocs.io/)** — Container management
- **[GitHub API](https://docs.github.com/en/rest)** — CI/CD trigger

---

## 📄 License

MIT — bebas dipakai dan dimodifikasi.

---

<div align="center">
  <sub>Dibuat sebagai proyek portofolio oleh <a href="https://github.com/moran2-cyber">Moran</a></sub>
</div>
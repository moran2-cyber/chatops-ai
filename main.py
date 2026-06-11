"""
ChatOps AI — Entry Point
Jalankan: python main.py
"""

import logging
import os
import sys

from dotenv import load_dotenv

# load_dotenv() HARUS jalan sebelum import apapun yang butuh env variable
load_dotenv()

from slack_bolt.adapter.socket_mode import SocketModeHandler

from bot.slack_handler import create_app, register_handlers

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("chatops")


# ─── Validasi env ────────────────────────────────────────────────────────────
def validate_env() -> None:
    """Pastikan semua env variable wajib sudah diisi sebelum bot jalan."""
    required = {
        "SLACK_BOT_TOKEN": "Token bot Slack (xoxb-...)",
        "SLACK_APP_TOKEN": "Token app Socket Mode (xapp-...)",
    }
    missing = [f"  • {key} — {desc}" for key, desc in required.items() if not os.getenv(key)]
    if missing:
        logger.error("Environment variable berikut belum diisi di .env:\n%s", "\n".join(missing))
        sys.exit(1)


# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    validate_env()

    app = create_app()
    register_handlers(app)

    logger.info("🤖 ChatOps AI mulai berjalan...")
    logger.info("   Mode    : Socket Mode (tidak perlu public URL)")
    logger.info("   Bot     : siap menerima mention di Slack")
    logger.info("   Ketik Ctrl+C untuk berhenti")

    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])

    try:
        handler.start()
    except KeyboardInterrupt:
        logger.info("Bot dihentikan.")
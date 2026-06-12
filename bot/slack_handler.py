"""
bot/slack_handler.py

Handler utama untuk semua event Slack.
Sudah distruktur untuk mudah disambung ke AI Brain (orchestrator.py) di tahap berikutnya.
"""

import logging
import os
import re
from typing import Any

from slack_bolt import App
from slack_sdk.errors import SlackApiError

from ai.orchestrator import process_command

logger = logging.getLogger("chatops.handler")

# ─── Inisialisasi App ────────────────────────────────────────────────────────
# App dibuat via create_app() yang dipanggil dari main.py SETELAH load_dotenv()
# supaya env variable sudah terbaca saat App() diinisialisasi.

def create_app() -> App:
    token = os.environ.get("SLACK_BOT_TOKEN")
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET", "")
    return App(token=token, signing_secret=signing_secret)


def register_handlers(app: App) -> None:
    """Daftarkan semua event handler ke instance App yang sudah dibuat."""

    @app.event("app_mention")
    def handle_mention(event: dict, say: Any, client: Any) -> None:
        user_id: str = event.get("user", "unknown")
        raw_text: str = event.get("text", "")
        channel: str = event.get("channel", "")
        thread_ts: str = event.get("thread_ts", event.get("ts", ""))

        command = clean_text(raw_text)

        if not command:
            say(blocks=build_help_block("devopsbot"), thread_ts=thread_ts)
            return

        logger.info("Perintah dari @%s: %s", user_id, command)

        try:
            client.reactions_add(channel=channel, name="hourglass_flowing_sand", timestamp=event["ts"])
        except SlackApiError:
            pass

        # Proses dengan AI Brain
        ai_response = process_command(command, user_id)
        response_blocks = build_response_block(
            title="DevOps Bot",
            body=ai_response,
            status="success",
        )
        say(blocks=response_blocks, thread_ts=thread_ts)

        try:
            client.reactions_remove(channel=channel, name="hourglass_flowing_sand", timestamp=event["ts"])
            client.reactions_add(channel=channel, name="white_check_mark", timestamp=event["ts"])
        except SlackApiError:
            pass

        logger.info("Respons dikirim ke @%s", user_id)

    @app.event("message")
    def handle_dm(event: dict, say: Any) -> None:
        if event.get("bot_id") or event.get("subtype"):
            return

        user_id: str = event.get("user", "unknown")
        raw_text: str = event.get("text", "")
        command = clean_text(raw_text)

        if not command:
            return

        logger.info("DM dari @%s: %s", user_id, command)
        ai_response = process_command(command, user_id)
        response_blocks = build_response_block(title="DevOps Bot", body=ai_response, status="success")
        say(blocks=response_blocks)

    @app.error
    def global_error_handler(error: Exception, body: dict, logger: logging.Logger) -> None:
        logger.exception("Error tidak tertangani: %s | body: %s", error, body)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Hapus mention bot dari teks sehingga AI hanya dapat perintah bersih."""
    return re.sub(r"<@[A-Z0-9]+>", "", text).strip()


def build_ack_block(user_id: str, command: str) -> list[dict]:
    """Pesan 'sedang diproses' yang dikirim instan saat perintah diterima."""
    return [
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"⏳ <@{user_id}> mengirim: *{command[:80]}{'...' if len(command) > 80 else ''}*",
                }
            ],
        }
    ]


def build_response_block(
    title: str,
    body: str,
    status: str = "success",  # "success" | "error" | "warning" | "info"
    fields: list[dict] | None = None,
    actions: list[dict] | None = None,
) -> list[dict]:
    """
    Builder terpusat untuk semua respons bot.
    Menggunakan Slack Block Kit supaya rapi dan konsisten.
    """
    icon_map = {"success": "✅", "error": "❌", "warning": "⚠️", "info": "ℹ️"}

    header_block: dict[str, Any] = {
        "type": "header",
        "text": {"type": "plain_text", "text": f"{icon_map.get(status, 'ℹ️')} {title}"},
    }

    section_block: dict[str, Any] = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": body},
    }

    blocks: list[dict] = [header_block, section_block]

    # Tambah fields opsional (key-value 2 kolom)
    if fields:
        blocks.append({
            "type": "section",
            "fields": [{"type": "mrkdwn", "text": f"*{f['key']}*\n{f['value']}"} for f in fields],
        })

    blocks.append({"type": "divider"})

    # Tambah action buttons opsional (untuk approval workflow nanti)
    if actions:
        blocks.append({"type": "actions", "elements": actions})

    return blocks


def build_help_block(bot_name: str) -> list[dict]:
    """Tampilkan daftar perintah yang tersedia."""
    commands = [
        ("deploy `<service>` `<tag>`", "Deploy atau update service Docker"),
        ("log `<service>` `[N baris]`", "Tampilkan log terbaru container"),
        ("status `[service]`", "Cek status semua service atau satu service"),
        ("scale `<service>` `<N>`", "Scale container ke N replika"),
        ("rollback `<service>`", "Rollback service ke versi sebelumnya"),
        ("help", "Tampilkan pesan ini"),
    ]
    command_text = "\n".join([f"• `@{bot_name} {cmd}` — {desc}" for cmd, desc in commands])

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🤖 ChatOps AI — Daftar Perintah"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "Mention bot diikuti perintah dalam bahasa natural. Contoh:\n"
                    f"_@{bot_name} deploy backend ke production_"
                ),
            },
        },
        {"type": "divider"},
        {"type": "section", "text": {"type": "mrkdwn", "text": command_text}},
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "💡 AI akan memahami variasi bahasa natural — tidak perlu format persis.",
                }
            ],
        },
    ]


# ─── Router Perintah ─────────────────────────────────────────────────────────
# Tahap ini: routing sederhana berbasis keyword.
# Tahap berikutnya: ganti `route_command()` dengan panggilan ke AI orchestrator.

def route_command(command: str, user_id: str) -> tuple[str, list[dict]]:
    """
    Routing perintah sementara sebelum AI Brain tersambung.
    Return: (log_label, blocks)
    """
    cmd_lower = command.lower()

    # ── deploy ──
    if any(word in cmd_lower for word in ["deploy", "rilis", "update service"]):
        return "deploy", build_response_block(
            title="Simulasi Deploy",
            body=(
                "Perintah *deploy* diterima.\n\n"
                "```\n"
                "Tahap ini: routing keyword aktif\n"
                "Tahap berikutnya: AI Brain akan parsing service & tag otomatis\n"
                "```"
            ),
            status="info",
            fields=[
                {"key": "Dikirim oleh", "value": f"<@{user_id}>"},
                {"key": "Status", "value": "Menunggu AI Brain"},
            ],
        )

    # ── log ──
    if any(word in cmd_lower for word in ["log", "error", "tail"]):
        return "log", build_response_block(
            title="Simulasi Log Viewer",
            body=(
                "Perintah *log* diterima.\n\n"
                "```\n"
                "[2024-01-15 10:23:41] INFO  Server started on :8080\n"
                "[2024-01-15 10:23:42] INFO  Connected to database\n"
                "[2024-01-15 10:24:01] WARN  Response time 450ms (threshold: 300ms)\n"
                "```\n"
                "_Log dummy — akan terhubung ke Docker SDK di tahap berikutnya._"
            ),
            status="info",
            fields=[
                {"key": "Container", "value": "belum tersambung"},
                {"key": "Baris", "value": "3 (contoh)"},
            ],
        )

    # ── status / health ──
    if any(word in cmd_lower for word in ["status", "cek", "health", "ping", "aktif"]):
        return "status", build_response_block(
            title="Status Service (Simulasi)",
            body="Semua service dalam kondisi normal.",
            status="success",
            fields=[
                {"key": "backend", "value": "🟢 UP — 12ms"},
                {"key": "frontend", "value": "🟢 UP — 8ms"},
                {"key": "database", "value": "🟢 UP — 2ms"},
                {"key": "redis", "value": "🟡 DEGRADED — 95ms"},
            ],
        )

    # ── scale ──
    if any(word in cmd_lower for word in ["scale", "replika", "instance"]):
        return "scale", build_response_block(
            title="Simulasi Scale",
            body=(
                "Perintah *scale* diterima.\n"
                "_AI Brain akan parsing nama service dan jumlah replika secara otomatis._"
            ),
            status="info",
            fields=[
                {"key": "Dikirim oleh", "value": f"<@{user_id}>"},
                {"key": "Status", "value": "Menunggu AI Brain"},
            ],
        )

    # ── rollback ──
    if any(word in cmd_lower for word in ["rollback", "balik", "revert"]):
        return "rollback", build_response_block(
            title="⚠️ Simulasi Rollback",
            body=(
                "Perintah *rollback* diterima.\n\n"
                "Di tahap production, aksi ini akan memerlukan konfirmasi tombol approval "
                "sebelum dieksekusi."
            ),
            status="warning",
            fields=[
                {"key": "Dikirim oleh", "value": f"<@{user_id}>"},
                {"key": "Approval", "value": "Akan aktif di tahap Safety"},
            ],
        )

    # ── help ──
    if "help" in cmd_lower or "bantuan" in cmd_lower:
        return "help", build_help_block("devopsbot")

    # ── fallback / tidak dikenali ──
    return "unknown", build_response_block(
        title="Perintah Tidak Dikenali",
        body=(
            f"Saya belum memahami: *{command[:100]}*\n\n"
            "Coba ketik `@devopsbot help` untuk melihat daftar perintah yang tersedia.\n\n"
            "_Setelah AI Brain tersambung, bot akan memahami bahasa natural apapun._"
        ),
        status="error",
    )
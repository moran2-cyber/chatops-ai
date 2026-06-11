"""
ai/tools/portomoran_tool.py

Tools khusus untuk mengontrol service porto-moran via Docker SDK.
Nama container diambil langsung dari docker-compose.yml porto-moran.
"""

import logging
import docker
from docker.errors import DockerException, NotFound
from langchain.tools import tool

logger = logging.getLogger("chatops.tools.portomoran")

# Mapping nama pendek → nama container nyata di docker-compose.yml
SERVICES = {
    "app":          "portomoran_app",
    "frontend":     "portomoran_app",
    "api":          "portomoran_api",
    "backend":      "portomoran_api",
    "db":           "portomoran_db",
    "database":     "portomoran_db",
    "redis":        "portomoran_redis",
    "prometheus":   "portomoran_prometheus",
    "grafana":      "portomoran_grafana",
    "alertmanager": "portomoran_alertmanager",
    "cloudflared":  "portomoran_cloudflared",
    "node-exporter":"portomoran_node_exporter",
}

# Service yang BOLEH di-restart/stop via bot (yang lain read-only)
MUTABLE_SERVICES = {"portomoran_app", "portomoran_api"}

# Semua nama container porto-moran
ALL_CONTAINERS = set(SERVICES.values())


def _get_client():
    try:
        return docker.from_env()
    except DockerException as e:
        raise RuntimeError(f"Tidak bisa konek ke Docker: {e}") from e


def _resolve(service_name: str) -> str | None:
    """Resolve nama pendek ke nama container nyata."""
    key = service_name.lower().strip()
    # Coba exact match dulu
    if key in SERVICES:
        return SERVICES[key]
    # Coba partial match
    for short, full in SERVICES.items():
        if key in short or key in full:
            return full
    return None


@tool
def portomoran_status(service_name: str = "") -> str:
    """
    Cek status container porto-moran.
    Gunakan ketika user tanya status porto-moran, website portfolio, atau service tertentu.

    Args:
        service_name: Nama service (app/api/db/redis/grafana/dll).
                     Kosongkan untuk cek semua service porto-moran.
    """
    try:
        client = _get_client()

        if service_name:
            # Cek satu service
            container_name = _resolve(service_name)
            if not container_name:
                available = ", ".join(SERVICES.keys())
                return (
                    f"❌ Service `{service_name}` tidak dikenali.\n"
                    f"Service yang tersedia: {available}"
                )
            targets = [container_name]
        else:
            # Cek semua service porto-moran
            targets = list(ALL_CONTAINERS)

        lines = ["*🌐 Status Porto-Moran Services:*\n"]
        found_any = False

        for name in sorted(targets):
            try:
                c = client.containers.get(name)
                found_any = True
                status = c.status

                if status == "running":
                    health = c.attrs.get("State", {}).get("Health", {})
                    health_status = health.get("Status", "") if health else ""
                    if health_status == "unhealthy":
                        icon, label = "🟡", "RUNNING (unhealthy)"
                    else:
                        icon, label = "🟢", "RUNNING"
                elif status == "exited":
                    exit_code = c.attrs.get("State", {}).get("ExitCode", "?")
                    icon, label = "🔴", f"STOPPED (exit {exit_code})"
                else:
                    icon, label = "⚪", status.upper()

                # Cari nama pendek untuk display
                short = next((k for k, v in SERVICES.items() if v == name), name)
                lines.append(f"{icon} *{short}* (`{name}`)")
                lines.append(f"   Status: {label}")
                lines.append("")

            except NotFound:
                short = next((k for k, v in SERVICES.items() if v == name), name)
                lines.append(f"⚫ *{short}* — container tidak ditemukan")
                lines.append("")

        if not found_any and not service_name:
            return (
                "⚠️ Tidak ada container porto-moran yang ditemukan.\n"
                "Pastikan porto-moran sudah dijalankan dengan `docker compose up -d`."
            )

        return "\n".join(lines)

    except RuntimeError as e:
        return f"❌ {e}"
    except Exception as e:
        logger.exception("portomoran_status error: %s", e)
        return f"❌ Gagal cek status: {e}"


@tool
def portomoran_logs(service_name: str, lines: int = 30) -> str:
    """
    Ambil log terbaru dari container porto-moran.
    Gunakan ketika user ingin lihat log porto-moran, error website, atau API error.

    Args:
        service_name: Nama service (app/api/db/redis/grafana/dll).
        lines: Jumlah baris log (default 30, max 100).
    """
    try:
        client = _get_client()
        lines = min(lines, 100)

        container_name = _resolve(service_name)
        if not container_name:
            return f"❌ Service `{service_name}` tidak dikenali. Pilihan: {', '.join(SERVICES.keys())}"

        try:
            container = client.containers.get(container_name)
        except NotFound:
            return f"❌ Container `{container_name}` tidak ditemukan. Pastikan porto-moran sudah jalan."

        raw = container.logs(tail=lines, timestamps=True).decode("utf-8", errors="replace")

        if not raw.strip():
            return f"📭 Tidak ada log terbaru dari `{container_name}`."

        if len(raw) > 2800:
            raw = "...(dipotong)...\n" + raw[-2800:]

        short = next((k for k, v in SERVICES.items() if v == container_name), container_name)
        return (
            f"*Log porto-moran `{short}` — {lines} baris terakhir:*\n"
            f"```\n{raw.strip()}\n```"
        )

    except RuntimeError as e:
        return f"❌ {e}"
    except Exception as e:
        logger.exception("portomoran_logs error: %s", e)
        return f"❌ Gagal ambil log: {e}"


@tool
def portomoran_restart(service_name: str) -> str:
    """
    Restart container porto-moran yang bermasalah.
    Hanya bisa restart app (frontend) dan api (backend).
    Database dan Redis TIDAK boleh di-restart via bot untuk keamanan data.

    Args:
        service_name: Nama service yang akan di-restart (app/frontend/api/backend).
    """
    try:
        client = _get_client()

        container_name = _resolve(service_name)
        if not container_name:
            return f"❌ Service `{service_name}` tidak dikenali."

        # Safety guard — hanya app dan api yang boleh di-restart
        if container_name not in MUTABLE_SERVICES:
            short = next((k for k, v in SERVICES.items() if v == container_name), container_name)
            return (
                f"⛔ Service `{short}` tidak bisa di-restart via bot.\n"
                f"Hanya `app` (frontend) dan `api` (backend) yang diizinkan.\n"
                f"Untuk database/redis, lakukan manual di server."
            )

        try:
            container = client.containers.get(container_name)
        except NotFound:
            return f"❌ Container `{container_name}` tidak ditemukan."

        container.restart(timeout=15)

        short = next((k for k, v in SERVICES.items() if v == container_name), container_name)
        return (
            f"✅ *Restart berhasil!*\n"
            f"   Service : `{short}` (`{container_name}`)\n"
            f"   Status  : Container sudah direstart dan berjalan kembali\n"
            f"   Tip     : Gunakan `cek status {short}` untuk verifikasi"
        )

    except RuntimeError as e:
        return f"❌ {e}"
    except Exception as e:
        logger.exception("portomoran_restart error: %s", e)
        return f"❌ Restart gagal: {e}"
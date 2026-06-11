"""
ai/tools/log_tool.py
Tool untuk membaca log dari container Docker.
"""

import logging
import docker
from docker.errors import DockerException
from langchain.tools import tool

logger = logging.getLogger("chatops.tools.log")


def _get_client():
    try:
        return docker.from_env()
    except DockerException as e:
        raise RuntimeError(f"Tidak bisa konek ke Docker: {e}") from e


@tool
def get_logs(service_name: str, lines: int = 30) -> str:
    """
    Ambil log terbaru dari container Docker.
    Gunakan ketika user ingin melihat log, error, atau output container.

    Args:
        service_name: Nama container yang ingin dilihat lognya.
        lines: Jumlah baris log (default 30, max 100).
    """
    try:
        client = _get_client()
        lines = min(lines, 100)

        all_containers = client.containers.list(all=True)
        matched = [c for c in all_containers if service_name.lower() in c.name.lower()]

        if not matched:
            available = ", ".join(f"`{c.name}`" for c in all_containers) or "tidak ada"
            return (
                f"❌ Container `{service_name}` tidak ditemukan.\n"
                f"Container tersedia: {available}"
            )

        container = matched[0]
        raw_logs = container.logs(tail=lines, timestamps=True).decode("utf-8", errors="replace")

        if not raw_logs.strip():
            return f"📭 Container `{container.name}` tidak punya log terbaru."

        if len(raw_logs) > 2800:
            raw_logs = "...(dipotong)...\n" + raw_logs[-2800:]

        return (
            f"*Log `{container.name}` — {lines} baris terakhir:*\n"
            f"```\n{raw_logs.strip()}\n```"
        )

    except RuntimeError as e:
        return f"❌ {e}"
    except Exception as e:
        logger.exception("log_tool error: %s", e)
        return f"❌ Gagal mengambil log: {e}"
"""
ai/tools/health_tool.py
 
Tool untuk mengecek status dan kesehatan service/container Docker.
"""

import logging
from typing import Optional

import docker
from docker.errors import DockerException, NotFound
from langchain.tools import tool

logger = logging.getLogger("chatops.tools.health")


def _get_docker_client():
    try:
        return docker.from_env()
    except DockerException as e:
        raise RuntimeError(f"Tidak bisa connect ke docker: {e}") from e


@tool
def check_health(service_name: Optional[str] = None) -> str:
    """
    Cek status dan kesehatan container Docker.
    Gunakan tool ini ketika user bertanya tentang status service,
    apakah service masih hidup, atau health check.
    
    Args:
        service_name: Nama container yang ingin dicek. 
                     Kosongkan untuk cek semua container.
    """
    try:
        client = _get_docker_client()
        containers = client.containers.list(all=True)

        if not containers:
            return "Tidak ada container ditemukan."

        # filter berdasarkan nama kalau disebutkan
        if service_name:
            containers = [
                c for c in containers
                if service_name.lower() in c.name.lower()
            ]
            if not containers:
                return f"Tidak ditemukan container dengan nama '{service_name}'."

        lines = ["Status container docker:*\n"]

        for container in containers:
            status = container.status # running, exited, paused, dll

            # emoji berdasrkan status
            if status == "running":
                # cek health kalau ada
                health = container.attrs.get("State", {}).get("Health", {})
                health_status = health.get("Stauts","") if health else ""

                if health_status == "unhealthy":
                    icon = "🟡"
                    status_text = "RUNNING (unhealthy)"
                else:
                    icon = "🟢"
                    status_text = "RUNNING"
            elif status == "exited":
                icon = "🔴"
                exit_code = container.attrs.get("State", {}).get("ExitCode", "?")
                status_text = f"STOPPED (exit {exit_code})"
            elif status == "paused":
                icon = "⏸️"
                status_text = "PAUSED"
            else:
                icon = "⚪"
                status_text = status.upper()
 
            # Ambil image name
            image = container.image.tags[0] if container.image.tags else "unknown"
 
            lines.append(f"{icon} *{container.name}*")
            lines.append(f"   Status : {status_text}")
            lines.append(f"   Image  : `{image}`")
            lines.append("")
 
        return "\n".join(lines)
 
    except RuntimeError as e:
        return f"❌ {e}"
    except Exception as e:
        logger.exception("health_tool error: %s", e)
        return f"❌ Gagal mengecek status: {e}"

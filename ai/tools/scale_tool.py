"""
ai/tools/scale_tool.py

Tool untuk scaling container Docker.
"""

import logging

import docker
from docker.errors import DockerException
from langchain.tools import tool

logger = logging.getLogger("chatops.tools.scale")


def _get_docker_client():
    try:
        return docker.from_env()
    except DockerException as e:
        raise RuntimeError(f"Tidak bisa konek ke Docker: {e}") from e


@tool
def scale_service(service_name: str, replicas: int) -> str:
    """
    Scale jumlah replika container Docker.
    Gunakan tool ini ketika user ingin menambah atau mengurangi jumlah instance/replika service.
    
    Args:
        service_name: Nama service yang akan di-scale.
        replicas: Jumlah replika yang diinginkan (1-10).
    """
    try:
        # Validasi jumlah replika
        if replicas < 1:
            return "❌ Jumlah replika minimal 1."
        if replicas > 10:
            return "⚠️ Jumlah replika maksimal 10 untuk keamanan. Hubungi admin untuk scale lebih besar."

        client = _get_docker_client()

        all_containers = client.containers.list(all=True)
        matched = [c for c in all_containers if service_name.lower() in c.name.lower()]

        if not matched:
            return f"❌ Container `{service_name}` tidak ditemukan."

        # Hitung container yang sudah berjalan untuk service ini
        running = [c for c in matched if c.status == "running"]
        current_count = len(running)

        if current_count == replicas:
            return f"ℹ️ Service `{service_name}` sudah berjalan dengan {replicas} replika."

        # Ambil config dari container pertama sebagai template
        template = matched[0]
        image = template.image.tags[0] if template.image.tags else template.image.short_id
        env = template.attrs.get("Config", {}).get("Env", [])
        base_name = template.name.rstrip("0123456789-_")

        logger.info("Scale %s: %d → %d replika", service_name, current_count, replicas)

        if replicas > current_count:
            # Scale UP — tambah container baru
            added = 0
            for i in range(current_count + 1, replicas + 1):
                client.containers.run(
                    image,
                    name=f"{base_name}-{i}",
                    detach=True,
                    environment=env,
                    restart_policy={"Name": "unless-stopped"},
                )
                added += 1

            return (
                f"✅ *Scale UP berhasil!*\n"
                f"   Service  : `{service_name}`\n"
                f"   Sebelum  : {current_count} replika\n"
                f"   Sesudah  : {replicas} replika\n"
                f"   Ditambah : {added} container baru"
            )

        else:
            # Scale DOWN — stop container berlebih
            to_stop = running[replicas:]
            for c in to_stop:
                c.stop(timeout=5)
                c.remove()

            return (
                f"✅ *Scale DOWN berhasil!*\n"
                f"   Service   : `{service_name}`\n"
                f"   Sebelum   : {current_count} replika\n"
                f"   Sesudah   : {replicas} replika\n"
                f"   Dihentikan: {len(to_stop)} container"
            )

    except RuntimeError as e:
        return f"❌ {e}"
    except Exception as e:
        logger.exception("scale_tool error: %s", e)
        return f"❌ Scale gagal: {e}"
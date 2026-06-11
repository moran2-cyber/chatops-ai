"""
ai/tools/docker_tool.py

Tools untuk operasi deployment: deploy, restart, rollback.
"""

import logging
from typing import Optional

import docker
from docker.errors import DockerException, ImageNotFound, NotFound
from langchain.tools import tool

logger = logging.getLogger("chatops.tools.docker")


def _get_docker_client():
    try:
        return docker.from_env()
    except DockerException as e:
        raise RuntimeError(f"Tidak bisa konek ke Docker: {e}") from e


@tool
def deploy_service(service_name: str, image_tag: str = "latest") -> str:
    """
    Deploy atau update service Docker ke versi baru.
    Gunakan tool ini ketika user ingin deploy, update, atau menjalankan service baru.
    Tool ini akan pull image terbaru lalu restart container dengan image baru.
    
    Args:
        service_name: Nama container yang akan di-deploy.
        image_tag: Tag image Docker yang akan digunakan (default: latest).
    """
    try:
        client = _get_docker_client()

        # Cari container yang sudah ada
        all_containers = client.containers.list(all=True)
        matched = [c for c in all_containers if service_name.lower() in c.name.lower()]

        if not matched:
            return (
                f"❌ Container `{service_name}` tidak ditemukan.\n"
                f"Pastikan nama service benar. Gunakan perintah `status` untuk melihat daftar container."
            )

        container = matched[0]
        old_image = container.image.tags[0] if container.image.tags else "unknown"

        # Ambil image name dari container yang ada
        image_name = container.image.tags[0].split(":")[0] if container.image.tags else service_name
        new_image = f"{image_name}:{image_tag}"

        logger.info("Deploy %s: %s → %s", container.name, old_image, new_image)

        # Pull image baru
        try:
            client.images.pull(image_name, tag=image_tag)
        except ImageNotFound:
            return f"❌ Image `{new_image}` tidak ditemukan di registry."

        # Simpan config container lama
        config = container.attrs
        ports = config.get("HostConfig", {}).get("PortBindings", {})
        env = config.get("Config", {}).get("Env", [])
        name = container.name

        # Stop dan hapus container lama
        container.stop(timeout=10)
        container.remove()

        # Jalankan container baru
        client.containers.run(
            new_image,
            name=name,
            detach=True,
            ports=ports,
            environment=env,
            restart_policy={"Name": "unless-stopped"},
        )

        return (
            f"✅ *Deploy berhasil!*\n"
            f"   Service : `{name}`\n"
            f"   Image lama : `{old_image}`\n"
            f"   Image baru : `{new_image}`\n"
            f"   Status : Container berjalan dengan image baru"
        )

    except RuntimeError as e:
        return f"❌ {e}"
    except Exception as e:
        logger.exception("deploy_tool error: %s", e)
        return f"❌ Deploy gagal: {e}"


@tool
def restart_service(service_name: str) -> str:
    """
    Restart container Docker yang bermasalah atau hang.
    Gunakan tool ini ketika user ingin restart service, atau service tidak merespons.
    
    Args:
        service_name: Nama container yang akan di-restart.
    """
    try:
        client = _get_docker_client()

        all_containers = client.containers.list(all=True)
        matched = [c for c in all_containers if service_name.lower() in c.name.lower()]

        if not matched:
            return f"❌ Container `{service_name}` tidak ditemukan."

        container = matched[0]
        logger.info("Restart container: %s", container.name)

        container.restart(timeout=10)

        return (
            f"✅ *Restart berhasil!*\n"
            f"   Service : `{container.name}`\n"
            f"   Status  : Container sudah direstart dan berjalan kembali"
        )

    except RuntimeError as e:
        return f"❌ {e}"
    except Exception as e:
        logger.exception("restart_tool error: %s", e)
        return f"❌ Restart gagal: {e}"


@tool
def rollback_service(service_name: str) -> str:
    """
    Rollback service Docker ke image versi sebelumnya.
    Gunakan tool ini ketika user ingin rollback atau balik ke versi sebelumnya setelah deploy bermasalah.
    
    Args:
        service_name: Nama container yang akan di-rollback.
    """
    try:
        client = _get_docker_client()

        all_containers = client.containers.list(all=True)
        matched = [c for c in all_containers if service_name.lower() in c.name.lower()]

        if not matched:
            return f"❌ Container `{service_name}` tidak ditemukan."

        container = matched[0]
        current_image = container.image.tags[0] if container.image.tags else "unknown"

        # Cari image sebelumnya dari history
        image_name = current_image.split(":")[0] if ":" in current_image else current_image
        all_images = client.images.list(name=image_name)

        if len(all_images) < 2:
            return (
                f"⚠️ Tidak ada image lama untuk rollback `{service_name}`.\n"
                f"Hanya ditemukan satu versi image: `{current_image}`"
            )

        # Ambil image sebelumnya (urutan terbaru ke lama)
        all_images.sort(key=lambda x: x.attrs.get("Created", ""), reverse=True)
        previous_image = all_images[1]
        previous_tag = previous_image.tags[0] if previous_image.tags else previous_image.short_id

        logger.info("Rollback %s: %s → %s", container.name, current_image, previous_tag)

        # Simpan config
        config = container.attrs
        ports = config.get("HostConfig", {}).get("PortBindings", {})
        env = config.get("Config", {}).get("Env", [])
        name = container.name

        # Stop, remove, jalankan dengan image lama
        container.stop(timeout=10)
        container.remove()

        client.containers.run(
            previous_tag,
            name=name,
            detach=True,
            ports=ports,
            environment=env,
            restart_policy={"Name": "unless-stopped"},
        )

        return (
            f"✅ *Rollback berhasil!*\n"
            f"   Service      : `{name}`\n"
            f"   Dari image   : `{current_image}`\n"
            f"   Ke image     : `{previous_tag}`\n"
            f"   Status       : Container berjalan dengan versi sebelumnya"
        )

    except RuntimeError as e:
        return f"❌ {e}"
    except Exception as e:
        logger.exception("rollback_tool error: %s", e)
        return f"❌ Rollback gagal: {e}"
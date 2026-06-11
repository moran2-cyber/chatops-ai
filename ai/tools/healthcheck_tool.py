"""
ai/tools/healthcheck_tool.py

Tool untuk health check URL production porto-moran via Cloudflare.
Ping endpoint dari internet — bukan dari Docker lokal.
"""

import logging
import time
import urllib.request
import urllib.error
from langchain.tools import tool

logger = logging.getLogger("chatops.tools.healthcheck")

# Endpoint production porto-moran
ENDPOINTS = {
    "frontend": "https://moran-porto.my.id/health",
    "website":  "https://moran-porto.my.id/health",
    "app":      "https://moran-porto.my.id/health",
    "api":      "https://api.moran-porto.my.id/health",
    "backend":  "https://api.moran-porto.my.id/health",
    "grafana":  "https://monitoring.moran-porto.my.id",
}


def _ping(url: str, timeout: int = 10) -> tuple[int, float]:
    """Ping URL, return (http_status_code, response_time_ms)."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ChatOps-HealthCheck/1.0"},
    )
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = (time.time() - start) * 1000
            return resp.status, round(elapsed, 1)
    except urllib.error.HTTPError as e:
        elapsed = (time.time() - start) * 1000
        return e.code, round(elapsed, 1)
    except Exception:
        elapsed = (time.time() - start) * 1000
        return 0, round(elapsed, 1)


@tool
def healthcheck_production(service_name: str = "") -> str:
    """
    Cek kesehatan endpoint production porto-moran dari internet via Cloudflare.
    Berbeda dengan cek Docker lokal — ini benar-benar ping dari luar.
    Gunakan ketika user tanya apakah website bisa diakses, production sehat, atau URL down.

    Args:
        service_name: Nama service (frontend/api/grafana).
                     Kosongkan untuk cek semua endpoint.
    """
    if service_name:
        key = service_name.lower().strip()
        if key not in ENDPOINTS:
            available = ", ".join(set(ENDPOINTS.keys()))
            return f"❌ Endpoint `{service_name}` tidak dikenali. Pilihan: {available}"
        targets = {key: ENDPOINTS[key]}
    else:
        # Deduplicate — cek tiap URL unik sekali saja
        seen = set()
        targets = {}
        for name, url in ENDPOINTS.items():
            if url not in seen:
                seen.add(url)
                targets[name] = url

    lines = ["*🌐 Health Check Production porto-moran:*\n"]

    all_ok = True
    for name, url in targets.items():
        code, ms = _ping(url)

        if code == 200:
            icon = "✅"
            label = f"UP — HTTP {code} · {ms}ms"
        elif code in (301, 302, 307, 308):
            icon = "🔀"
            label = f"REDIRECT — HTTP {code} · {ms}ms"
        elif code >= 500:
            icon = "🔴"
            label = f"SERVER ERROR — HTTP {code} · {ms}ms"
            all_ok = False
        elif code >= 400:
            icon = "🟡"
            label = f"CLIENT ERROR — HTTP {code} · {ms}ms"
            all_ok = False
        elif code == 0:
            icon = "⚫"
            label = "TIDAK DAPAT DIJANGKAU (timeout/DNS error)"
            all_ok = False
        else:
            icon = "❓"
            label = f"HTTP {code} · {ms}ms"

        lines.append(f"{icon} *{name}*")
        lines.append(f"   URL    : `{url}`")
        lines.append(f"   Status : {label}")
        lines.append("")

    if all_ok:
        lines.append("_Semua endpoint production dalam kondisi sehat_ ✅")
    else:
        lines.append("_⚠️ Ada endpoint yang bermasalah — periksa log dengan `log api` atau `log app`_")

    return "\n".join(lines)
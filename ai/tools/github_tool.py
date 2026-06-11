"""
ai/tools/github_tool.py

Tool untuk trigger GitHub Actions workflow porto-moran.
Pakai GitHub API — tidak perlu SSH ke server sama sekali.
"""

import logging
import os
import urllib.request
import urllib.error
import json
from langchain.tools import tool

logger = logging.getLogger("chatops.tools.github")

REPO = "moran2-cyber/portomoran"
WORKFLOW_FILE = "deploy.yml"
BRANCH = "main"


def _github_api(method: str, endpoint: str, data: dict | None = None) -> tuple[int, dict]:
    """Helper untuk GitHub API call."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN belum diset di .env\n"
            "Buat token di: github.com/settings/tokens → New token → pilih scope `workflow`"
        )

    url = f"https://api.github.com{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            detail = json.loads(raw).get("message", str(e))
        except Exception:
            detail = str(e)
        raise RuntimeError(f"GitHub API error {e.code}: {detail}") from e


@tool
def github_deploy(environment: str = "production") -> str:
    """
    Trigger GitHub Actions untuk deploy porto-moran ke production.
    Gunakan ketika user ingin deploy porto-moran, update website, atau rilis versi baru.

    Args:
        environment: Environment target deploy (default: production).
    """
    try:
        status, _ = _github_api(
            "POST",
            f"/repos/{REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches",
            {"ref": BRANCH, "inputs": {}},
        )

        if status == 204:
            return (
                f"🚀 *Deploy porto-moran berhasil di-trigger!*\n"
                f"   Repo       : `{REPO}`\n"
                f"   Branch     : `{BRANCH}`\n"
                f"   Environment: `{environment}`\n\n"
                f"Pipeline sedang berjalan di GitHub Actions.\n"
                f"Pantau progresnya di: https://github.com/{REPO}/actions\n\n"
                f"_Estimasi selesai: 3–5 menit_"
            )

        return f"⚠️ Unexpected response dari GitHub: HTTP {status}"

    except RuntimeError as e:
        return f"❌ {e}"
    except Exception as e:
        logger.exception("github_deploy error: %s", e)
        return f"❌ Gagal trigger deploy: {e}"


@tool
def github_workflow_status() -> str:
    """
    Cek status workflow GitHub Actions porto-moran terbaru.
    Gunakan ketika user tanya apakah deploy sudah selesai, status CI/CD, atau pipeline.
    """
    try:
        status, data = _github_api(
            "GET",
            f"/repos/{REPO}/actions/runs?per_page=5&branch={BRANCH}",
        )

        runs = data.get("workflow_runs", [])
        if not runs:
            return "📭 Belum ada workflow run yang ditemukan di GitHub Actions."

        lines = [f"*📋 GitHub Actions — {REPO} (5 terbaru):*\n"]

        status_icon = {
            "success":    "✅",
            "failure":    "❌",
            "in_progress":"⏳",
            "queued":     "🕐",
            "cancelled":  "🚫",
            "skipped":    "⏭️",
        }

        for run in runs[:5]:
            conclusion = run.get("conclusion") or run.get("status", "unknown")
            icon = status_icon.get(conclusion, "❓")
            name = run.get("display_title", run.get("name", "Unknown"))[:50]
            created = run.get("created_at", "")[:16].replace("T", " ")
            run_url = run.get("html_url", "")
            sha = run.get("head_sha", "")[:7]

            lines.append(f"{icon} *{name}*")
            lines.append(f"   Status : `{conclusion}` · SHA: `{sha}`")
            lines.append(f"   Waktu  : {created} UTC")
            lines.append(f"   Link   : {run_url}")
            lines.append("")

        return "\n".join(lines)

    except RuntimeError as e:
        return f"❌ {e}"
    except Exception as e:
        logger.exception("github_workflow_status error: %s", e)
        return f"❌ Gagal cek workflow: {e}"

"""
ai/orchestrator.py
AI Brain menggunakan LangGraph create_react_agent.
"""

import logging
import os

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

# Generic DevOps tools
from ai.tools.docker_tool import deploy_service, restart_service, rollback_service
from ai.tools.health_tool import check_health
from ai.tools.log_tool import get_logs
from ai.tools.scale_tool import scale_service

# Porto-moran specific tools
from ai.tools.portomoran_tool import portomoran_status, portomoran_logs, portomoran_restart
from ai.tools.github_tool import github_deploy, github_workflow_status
from ai.tools.healthcheck_tool import healthcheck_production

logger = logging.getLogger("chatops.ai")

SYSTEM_PROMPT = """Kamu adalah DevOps Bot — asisten AI untuk operasi infrastruktur tim Moran.

Kamu mengelola DUA environment:
1. Container Docker generik (check_health, get_logs, deploy_service, scale_service)
2. Porto-moran production (portomoran_status, portomoran_logs, portomoran_restart,
   github_deploy, github_workflow_status, healthcheck_production)

Panduan penting:
- Kalau user sebut "porto-moran", "website", "portfolio", "production" → pakai tools portomoran_*
- Kalau user sebut "deploy production" atau "rilis" → pakai github_deploy
- Kalau user tanya "website bisa diakses?" atau "production sehat?" → pakai healthcheck_production
- Kalau user tanya status workflow / CI/CD → pakai github_workflow_status
- Untuk container Docker lain → pakai tools generik

Safety rules:
- JANGAN restart db atau redis porto-moran via bot
- Selalu konfirmasi dulu sebelum deploy ke production
- Berikan respons singkat, jelas, dalam Bahasa Indonesia

Selalu jawab dalam Bahasa Indonesia kecuali user pakai Bahasa Inggris."""

TOOLS = [
    # Generic
    check_health,
    get_logs,
    deploy_service,
    restart_service,
    scale_service,
    rollback_service,
    # Porto-moran
    portomoran_status,
    portomoran_logs,
    portomoran_restart,
    github_deploy,
    github_workflow_status,
    healthcheck_production,
]

_history: dict[str, list] = {}

def _get_history(user_id: str) -> list:
    if user_id not in _history:
        _history[user_id] = []
    return _history[user_id]

_agent = None

def get_agent():
    global _agent
    if _agent is None:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=os.environ.get("GOOGLE_API_KEY"),
            temperature=0,
        )
        _agent = create_react_agent(
            model=llm,
            tools=TOOLS,
            prompt=SYSTEM_PROMPT,
        )
    return _agent

def process_command(command: str, user_id: str) -> str:
    logger.info("AI memproses: user=%s | command=%s", user_id, command)
    try:
        agent = get_agent()
        history = _get_history(user_id)
        messages = history + [HumanMessage(content=command)]

        result = agent.invoke({"messages": messages})
        all_messages = result.get("messages", [])

        response = "Maaf, saya tidak bisa memproses perintah itu."
        for msg in reversed(all_messages):
            msg_type = type(msg).__name__
            if msg_type == "AIMessage" and msg.content and not getattr(msg, "tool_calls", None):
                response = msg.content
                break

        history.append(HumanMessage(content=command))
        history.append(all_messages[-1])
        _history[user_id] = history[-10:]

        logger.info("AI selesai: %s", response[:100])
        return response

    except Exception as e:
        logger.exception("AI error: %s", e)
        return f"❌ Error: `{type(e).__name__}: {str(e)[:200]}`"
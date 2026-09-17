"""Enterprise SLA Guardian demo agent for WSO2 Agent Manager.

The service uses only synthetic telecom service-assurance evidence. It is
read-only: it can assess risk and draft communications, but cannot send them or
make contractual, ticketing, escalation, or network changes.
"""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from mock_data import scenarios
from sla_llm import EnterpriseSLAGuardian

APP_VERSION = "1.0.0"
guardian = EnterpriseSLAGuardian()

app = FastAPI(
    title="Enterprise SLA Guardian",
    description=(
        "Read-only mock enterprise SLA risk assessment for WSO2 Agent Manager. "
        "Responses are model-synthesized from de-identified scenario data."
    ),
    version=APP_VERSION,
)


class ChatRequest(BaseModel):
    """Agent Manager's standard Chat Agent request contract."""

    message: str = Field(min_length=1, max_length=8000, description="SLA guardian request")
    session_id: str | None = Field(default=None, max_length=256)
    context: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Advisory response and safe, user-visible workflow milestones."""

    response: str
    development_steps: list[str]
    provider: str | None = None
    used_fallback: bool = False


@app.get("/health")
def health() -> dict[str, Any]:
    """Return readiness and non-sensitive provider metadata only."""
    return {
        "status": "ok",
        "agent": "enterprise-sla-guardian",
        "version": APP_VERSION,
        "llm": guardian.public_status(),
    }


@app.get("/scenarios")
def list_scenarios() -> dict[str, Any]:
    """List compact mock scenarios for demonstrations and evaluation."""
    return {"simulation": True, "read_only": True, "scenarios": scenarios()}


@app.get("/status")
def status() -> dict[str, Any]:
    """Expose non-sensitive runtime characteristics."""
    return {
        "simulation": True,
        "read_only": True,
        "llm": guardian.public_status(),
        "providers": ["gemini", "anthropic", "openai", "glm"],
        "history": "bounded in-memory history is retained per session_id",
        "console": "GET /console displays safe workflow milestones in a left panel",
        "human_approval": [
            "customer communications",
            "contractual classification",
            "service-credit commitments",
            "executive escalation",
            "network changes",
        ],
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Generate an evidence-grounded SLA advisory with no external side effects."""
    result = guardian.answer_with_metadata(request.message, request.context, request.session_id)
    return ChatResponse(
        response=result.response,
        development_steps=result.development_steps,
        provider=result.provider,
        used_fallback=result.used_fallback,
    )


@app.get("/console", response_class=HTMLResponse, include_in_schema=False)
def custom_console() -> str:
    """Provide an optional safe, standalone demo interface.

    The panel renders only auditable workflow milestones. It does not expose
    hidden model reasoning or credentials. Agent Manager's standard Try It
    experience continues to use `/chat` directly.
    """
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Enterprise SLA Guardian</title><style>
:root { color-scheme:dark; --bg:#0c1422; --panel:#131f32; --line:#2d405d; --text:#edf4ff; --muted:#a9b8ce; --accent:#7ed0ff; --warn:#ffd38a; }
* { box-sizing:border-box; } body { margin:0; min-height:100vh; background:var(--bg); color:var(--text); font:15px/1.55 system-ui,-apple-system,Segoe UI,sans-serif; }
.app { display:grid; grid-template-columns:300px minmax(0,1fr); min-height:100vh; } aside { padding:30px 24px; border-right:1px solid var(--line); background:#101b2c; } main { padding:34px; max-width:1000px; width:100%; margin:auto; }
h1 { font-size:24px; margin:0 0 6px; } h2 { font-size:14px; text-transform:uppercase; letter-spacing:.08em; color:var(--accent); margin:28px 0 12px; } p { color:var(--muted); margin:0 0 14px; } ol { padding-left:22px; color:var(--muted); } li { margin:10px 0; }
.badge { display:inline-block; font-size:12px; padding:3px 9px; border:1px solid var(--line); border-radius:999px; color:var(--accent); } textarea { width:100%; min-height:110px; padding:14px; border:1px solid var(--line); border-radius:10px; color:var(--text); background:#0b1728; resize:vertical; font:inherit; }
button { margin-top:12px; padding:10px 16px; border:0; border-radius:8px; background:var(--accent); color:#052032; font-weight:700; cursor:pointer; } button:disabled { opacity:.55; cursor:wait; } #answer { white-space:pre-wrap; background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:20px; min-height:80px; margin-top:22px; } .notice { color:var(--warn); font-size:13px; } @media(max-width:760px){.app{grid-template-columns:1fr}aside{border-right:0;border-bottom:1px solid var(--line)}}
</style></head><body><div class="app"><aside><span class="badge">Read-only simulation</span><h2>Development steps</h2><ol id="steps"><li>Awaiting an SLA assessment request.</li></ol><p class="notice">These are auditable workflow milestones, not private model reasoning.</p></aside><main><h1>Enterprise SLA Guardian</h1><p>Assess a synthetic SLA-risk scenario. The agent may prepare drafts, but never sends customer communications, classifies breaches, commits credits, escalates, or changes a network.</p><textarea id="message">Assess the SLA exposure for the enterprise SD-WAN latency trend, prioritize customers, and prepare a draft update subject to approval.</textarea><br><button id="send">Generate SLA advisory</button><div id="answer">Ready for a mock SLA assessment request.</div></main></div><script>
const send=document.getElementById('send'),input=document.getElementById('message'),answer=document.getElementById('answer'),steps=document.getElementById('steps');
function renderSteps(items){steps.replaceChildren();for(const item of items){const li=document.createElement('li');li.textContent=item;steps.appendChild(li);}}
send.addEventListener('click',async()=>{send.disabled=true;answer.textContent='Generating an evidence-grounded SLA advisory…';renderSteps(['Selecting a synthetic SLA scenario and preparing approved evidence.']);try{const r=await fetch('./chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:input.value,session_id:'standalone-sla-console',context:{scenario_id:'sdwan-latency-breach-risk'}})});const payload=await r.json();if(!r.ok)throw new Error(payload.detail||'Request failed');answer.textContent=payload.response;renderSteps(payload.development_steps||[]);}catch(error){answer.textContent=`Unable to obtain an advisory: ${error.message}`;renderSteps(['The request could not complete. No telecom or customer operation was executed.']);}finally{send.disabled=false;}});
</script></body></html>"""


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

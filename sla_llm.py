"""Model-backed, mock-data-grounded Enterprise SLA Guardian advisory service.

Evidence selection and fallback reports are deterministic. Language synthesis is
performed by a configurable model provider, but no model receives tools or
permissions to communicate externally or mutate telecom systems.
"""

from __future__ import annotations

import json
import os
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

from anthropic import (
    APIConnectionError as AnthropicAPIConnectionError,
    APIError as AnthropicAPIError,
    Anthropic,
    AuthenticationError as AnthropicAuthenticationError,
    RateLimitError as AnthropicRateLimitError,
)
from openai import APIConnectionError, APIError, AuthenticationError, OpenAI, RateLimitError

from finops_runtime import FinOpsRuntime, anthropic_usage, estimate_tokens, openai_usage
from sla_engine import ScenarioNotFound, build_sla_report, list_scenarios_report, select_scenario

DEFAULT_MODEL = "gemini-3-flash-preview"
DEFAULT_BASE_URL = "https://api.manus.im/api/llm-proxy/v1"
DEFAULT_ANTHROPIC_BASE_URL = "https://api.anthropic.com"
DEFAULT_HISTORY_MESSAGES = 6
MAX_HISTORY_MESSAGES = 12
SUPPORTED_PROVIDERS = ("gemini", "anthropic", "openai", "glm")

SYSTEM_PROMPT = """You are an Enterprise SLA Guardian for a telecom service-assurance team in a read-only simulation.

Use ONLY the supplied synthetic evidence. Do not invent contractual terms,
metrics, measurements, customer impacts, breach status, recovery times,
maintenance approvals, root causes, ticket events, or commercial commitments.
Clearly distinguish observed facts, risk projections, and hypotheses.

Give a concise Markdown advisory with these sections when relevant:
1. SLA risk assessment
2. Evidence and contractual exposure
3. Recommended operator-controlled actions
4. Draft customer communication guidance
5. Approval gates
6. Safety boundary

Customer messages must always be drafts for account-manager review. Never claim
to send a message, create or modify a ticket, classify a contractual breach,
offer a service credit, notify an executive, change network configuration, or
make a traffic, capacity, or routing decision. If asked to do so, state that
you can prepare a draft or advisory for authorized human approval only.

All information is synthetic, de-identified, and suitable only for demonstration.
"""

SAFETY_FOOTER = (
    "\n\n## Safety boundary\n"
    "This is a read-only simulation. No customer communication, SLA classification, "
    "service-credit commitment, ticket operation, escalation, or network change has been performed."
)


@dataclass(frozen=True)
class LLMSettings:
    """Non-sensitive provider connection metadata loaded only at runtime."""

    provider: str
    model: str
    base_url: str
    api_key: str | None
    max_tokens: int
    history_messages: int

    @classmethod
    def from_environment(cls) -> "LLMSettings":
        provider = _normalize_provider(os.getenv("LLM_PROVIDER", "gemini"))
        model = os.getenv("LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
        if provider == "anthropic":
            base_url = (os.getenv("LLM_PROVIDER_URL") or DEFAULT_ANTHROPIC_BASE_URL).rstrip("/")
            api_key = os.getenv("LLM_PROVIDER_KEY") or os.getenv("ANTHROPIC_API_KEY")
        else:
            base_url = (
                os.getenv("LLM_PROVIDER_URL") or os.getenv("OPENAI_API_BASE") or DEFAULT_BASE_URL
            ).rstrip("/")
            api_key = os.getenv("LLM_PROVIDER_KEY") or os.getenv("OPENAI_API_KEY")
        return cls(
            provider=provider,
            model=model,
            base_url=base_url,
            api_key=api_key,
            max_tokens=_bounded_int(os.getenv("LLM_MAX_TOKENS"), 900, 128, 2048),
            history_messages=_bounded_int(
                os.getenv("LLM_HISTORY_MESSAGES"), DEFAULT_HISTORY_MESSAGES, 0, MAX_HISTORY_MESSAGES
            ),
        )

    @property
    def protocol(self) -> str:
        return "anthropic-messages" if self.provider == "anthropic" else "openai-chat-completions"

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model and self.provider in SUPPORTED_PROVIDERS)

    def public_status(self) -> dict[str, Any]:
        return {
            "configured": self.configured,
            "provider": self.provider,
            "model": self.model,
            "protocol": self.protocol,
            "history_messages": self.history_messages,
            "supported_providers": list(SUPPORTED_PROVIDERS),
            "fallback": "deterministic mock-data SLA advisory",
        }


@dataclass(frozen=True)
class SLAResult:
    """Response plus safe user-visible workflow milestones."""

    response: str
    development_steps: list[str]
    provider: str | None
    used_fallback: bool


def _normalize_provider(value: str | None) -> str:
    aliases = {"z.ai": "glm", "zai": "glm", "z-ai": "glm"}
    provider = (value or "gemini").strip().lower()
    return aliases.get(provider, provider or "gemini")


def _bounded_int(value: str | None, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value or default)
    except ValueError:
        return default
    return min(maximum, max(minimum, parsed))


class SessionHistory:
    """Bounded, in-memory conversation history keyed by the Agent Manager session."""

    def __init__(self, max_messages: int) -> None:
        self._max_messages = max_messages
        self._items: dict[str, deque[dict[str, str]]] = defaultdict(
            lambda: deque(maxlen=max_messages or 1)
        )
        self._lock = threading.Lock()

    def messages(self, session_id: str | None) -> list[dict[str, str]]:
        if not session_id or not self._max_messages:
            return []
        with self._lock:
            return list(self._items[session_id])

    def add_turn(self, session_id: str | None, user: str, assistant: str) -> None:
        if not session_id or not self._max_messages:
            return
        with self._lock:
            self._items[session_id].append({"role": "user", "content": user})
            self._items[session_id].append({"role": "assistant", "content": assistant})


class ModelUnavailable(RuntimeError):
    """Raised when a provider cannot serve a request safely."""


class EnterpriseSLAGuardian:
    """Synthesize grounded SLA advisories with deterministic safe fallback behavior."""

    def __init__(self, settings: LLMSettings | None = None) -> None:
        self.settings = settings or LLMSettings.from_environment()
        self.history = SessionHistory(self.settings.history_messages)
        self._openai_client: OpenAI | None = None
        self._anthropic_client: Anthropic | None = None
        self.finops = FinOpsRuntime("enterprise-sla-guardian")

    def public_status(self) -> dict[str, Any]:
        return self.settings.public_status()

    def answer_with_metadata(
        self, message: str, context: dict[str, Any] | None, session_id: str | None
    ) -> SLAResult:
        context = context or {}
        normalized = message.lower().replace("_", "-").strip()
        if any(term in normalized for term in ("help", "list", "scenario", "mock data", "available")):
            response = list_scenarios_report()
            self.history.add_turn(session_id, message, response)
            return SLAResult(
                response=response,
                development_steps=[
                    "Recognized a scenario-discovery request.",
                    "Presented the available synthetic, read-only SLA simulations.",
                ],
                provider=None,
                used_fallback=False,
            )
        try:
            scenario = select_scenario(message, context)
        except ScenarioNotFound as exc:
            response = f"{exc}\n\n{list_scenarios_report()}"
            self.history.add_turn(session_id, message, response)
            return SLAResult(
                response=response,
                development_steps=[
                    "Validated the requested simulation identifier.",
                    "Returned the synthetic SLA scenario catalogue without model invocation.",
                ],
                provider=None,
                used_fallback=False,
            )

        steps = [
            "Selected the applicable synthetic SLA scenario from the request context.",
            "Retrieved only the selected mock telemetry, contract, maintenance, path, and problem evidence.",
            "Applied read-only, approval-gate, and no-external-communication constraints before response synthesis.",
        ]
        fallback = build_sla_report(scenario)
        if not self.settings.configured:
            steps.append("Model provider is not configured; returned the deterministic SLA advisory fallback.")
            self.history.add_turn(session_id, message, fallback)
            return SLAResult(fallback, steps, None, True)
        try:
            response = self._generate(message, scenario, session_id)
            steps.append(
                f"Synthesized an evidence-grounded SLA advisory through the configured {self.settings.provider} provider."
            )
            fallback_used = False
        except ModelUnavailable:
            response = fallback
            steps.append("The model invocation was unavailable; returned the deterministic SLA advisory fallback.")
            fallback_used = True
        self.history.add_turn(session_id, message, response)
        return SLAResult(response, steps, self.settings.provider if not fallback_used else None, fallback_used)

    def _generate(self, message: str, scenario: dict[str, Any], session_id: str | None) -> str:
        evidence = json.dumps(scenario, ensure_ascii=False, indent=2)
        user_message = (
            f"User request:\n{message}\n\n"
            f"Selected authoritative mock SLA evidence:\n```json\n{evidence}\n```\n\n"
            "Write a grounded advisory. Make contractual and communication approval gates explicit."
        )
        if self.settings.provider == "anthropic":
            response = self._generate_anthropic(user_message, session_id)
        else:
            response = self._generate_openai_compatible(user_message, session_id)
        return response + SAFETY_FOOTER

    def _generate_openai_compatible(self, user_message: str, session_id: str | None) -> str:
        messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(self.history.messages(session_id))
        messages.append({"role": "user", "content": user_message})
        preflight = self.finops.preflight(
            self.settings.model, estimate_tokens(messages), self.settings.max_tokens
        )
        if not preflight.allowed:
            raise ModelUnavailable(preflight.reason)
        try:
            completion = self._get_openai_client().chat.completions.create(
                model=self.settings.model, messages=messages, max_tokens=self.settings.max_tokens
            )
        except (APIConnectionError, AuthenticationError, RateLimitError, APIError) as exc:
            raise ModelUnavailable("Model request unavailable") from exc
        except Exception as exc:
            raise ModelUnavailable("Model request failed") from exc
        self.finops.record_usage(preflight.request_id, self.settings.model, *openai_usage(completion))
        text = completion.choices[0].message.content if completion.choices else None
        return _require_text(text)

    def _generate_anthropic(self, user_message: str, session_id: str | None) -> str:
        messages = self.history.messages(session_id)
        messages.append({"role": "user", "content": user_message})
        preflight = self.finops.preflight(
            self.settings.model, estimate_tokens(messages), self.settings.max_tokens
        )
        if not preflight.allowed:
            raise ModelUnavailable(preflight.reason)
        try:
            completion = self._get_anthropic_client().messages.create(
                model=self.settings.model,
                max_tokens=self.settings.max_tokens,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
        except (
            AnthropicAPIConnectionError,
            AnthropicAuthenticationError,
            AnthropicRateLimitError,
            AnthropicAPIError,
        ) as exc:
            raise ModelUnavailable("Model request unavailable") from exc
        except Exception as exc:
            raise ModelUnavailable("Model request failed") from exc
        self.finops.record_usage(preflight.request_id, self.settings.model, *anthropic_usage(completion))
        text = "".join(block.text for block in completion.content if getattr(block, "type", "") == "text")
        return _require_text(text)

    def _get_openai_client(self) -> OpenAI:
        if self._openai_client is None:
            if os.getenv("LLM_PROVIDER_AUTH_STYLE", "").lower() == "api-key":
                self._openai_client = OpenAI(
                    api_key="",
                    base_url=self.settings.base_url,
                    default_headers={"X-API-Key": self.settings.api_key or "", "Authorization": ""},
                )
            else:
                self._openai_client = OpenAI(api_key=self.settings.api_key, base_url=self.settings.base_url)
        return self._openai_client

    def _get_anthropic_client(self) -> Anthropic:
        if self._anthropic_client is None:
            self._anthropic_client = Anthropic(api_key=self.settings.api_key, base_url=self.settings.base_url)
        return self._anthropic_client


def _require_text(text: str | None) -> str:
    if not text or not text.strip():
        raise ModelUnavailable("Model returned no visible response")
    return text.strip()

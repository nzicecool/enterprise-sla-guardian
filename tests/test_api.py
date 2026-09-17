"""Tests for mock-data grounding, LLM adapters, and safety boundaries."""

from dataclasses import replace

from fastapi.testclient import TestClient

from main import app, guardian
from sla_llm import EnterpriseSLAGuardian, LLMSettings, ModelUnavailable

client = TestClient(app)


class FakeCompletion:
    class Choice:
        class Message:
            content = "## SLA risk assessment\nThe Platinum SD-WAN service is approaching its latency objective."

        message = Message()

    choices = [Choice()]


class FakeClient:
    class Chat:
        class Completions:
            def __init__(self) -> None:
                self.calls: list[dict] = []

            def create(self, **kwargs):
                self.calls.append(kwargs)
                return FakeCompletion()

        def __init__(self) -> None:
            self.completions = self.Completions()

    def __init__(self) -> None:
        self.chat = self.Chat()


class FakeAnthropicCompletion:
    class Block:
        type = "text"
        text = "## SLA risk assessment\nThe evidence supports an imminent Platinum-tier latency risk."

    content = [Block()]


class FakeAnthropicClient:
    class Messages:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return FakeAnthropicCompletion()

    def __init__(self) -> None:
        self.messages = self.Messages()


def test_health_exposes_no_secrets_and_defaults_to_gemini():
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["agent"] == "enterprise-sla-guardian"
    assert payload["llm"]["provider"] == "gemini"
    assert payload["llm"]["model"] == "gemini-3-flash-preview"
    assert "api_key" not in str(payload).lower()


def test_scenarios_are_explicitly_synthetic_and_read_only():
    response = client.get("/scenarios")
    assert response.status_code == 200
    payload = response.json()
    assert payload["simulation"] is True
    assert payload["read_only"] is True
    assert {row["scenario_id"] for row in payload["scenarios"]} == {
        "sdwan-latency-breach-risk",
        "planned-maintenance-degradation",
        "private-5g-congestion-risk",
    }


def test_model_response_is_grounded_has_history_and_safe_steps(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(guardian, "_get_openai_client", lambda: fake_client)
    first = client.post(
        "/chat",
        json={
            "message": "Assess the SD-WAN latency risk and draft an update.",
            "context": {"scenario_id": "sdwan-latency-breach-risk"},
            "session_id": "sla-history-test",
        },
    )
    second = client.post(
        "/chat",
        json={"message": "Which customer should be prioritized?", "session_id": "sla-history-test"},
    )
    assert first.status_code == 200
    payload = first.json()
    assert payload["provider"] == "gemini"
    assert payload["used_fallback"] is False
    assert "Safety boundary" in payload["response"]
    assert "No customer communication" in payload["response"]
    assert len(payload["development_steps"]) == 4
    assert all("reasoning" not in step.lower() for step in payload["development_steps"])
    assert second.status_code == 200
    messages = fake_client.chat.completions.calls[-1]["messages"]
    assert any(item["content"] == "Assess the SD-WAN latency risk and draft an update." for item in messages)
    assert "SLA-SIM-2026-0917-001" in messages[-1]["content"]
    assert "Meridian Capital Thailand" in messages[-1]["content"]


def test_anthropic_provider_uses_native_messages_api(monkeypatch):
    settings = LLMSettings(
        provider="anthropic",
        model="claude-test-model",
        base_url="https://api.anthropic.com",
        api_key="test-key",
        max_tokens=300,
        history_messages=4,
    )
    service = EnterpriseSLAGuardian(settings)
    fake_client = FakeAnthropicClient()
    monkeypatch.setattr(service, "_get_anthropic_client", lambda: fake_client)
    result = service.answer_with_metadata(
        "Assess private 5G risk",
        {"scenario_id": "private-5g-congestion-risk"},
        "anthropic-sla-test",
    )
    assert result.provider == "anthropic"
    assert result.used_fallback is False
    assert "Safety boundary" in result.response
    request = fake_client.messages.calls[0]
    assert request["model"] == "claude-test-model"
    assert "SLA-SIM-2026-0917-003" in request["messages"][-1]["content"]


def test_provider_alias_and_protocol_selection():
    default = LLMSettings.from_environment()
    assert default.provider == "gemini"
    assert replace(default, provider="glm").protocol == "openai-chat-completions"
    assert replace(default, provider="anthropic").protocol == "anthropic-messages"


def test_provider_failure_returns_a_deterministic_contractual_fallback(monkeypatch):
    monkeypatch.setattr(guardian, "_generate", lambda *args, **kwargs: (_ for _ in ()).throw(ModelUnavailable("offline")))
    response = client.post(
        "/chat",
        json={"message": "Assess SLA risk", "context": {"scenario_id": "sdwan-latency-breach-risk"}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["used_fallback"] is True
    assert payload["provider"] is None
    assert "SLA-SIM-2026-0917-001" in payload["response"]
    assert "Meridian Capital Thailand" in payload["response"]
    assert "READ-ONLY ADVISORY" in payload["response"]
    assert "No customer communication" in payload["response"]


def test_maintenance_scenario_distinguishes_exemption_from_breach(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(guardian, "_get_openai_client", lambda: fake_client)
    response = client.post(
        "/chat",
        json={
            "message": "Review the maintenance impact.",
            "context": {"scenario_id": "planned-maintenance-degradation"},
        },
    )
    assert response.status_code == 200
    evidence = fake_client.chat.completions.calls[-1]["messages"][-1]["content"]
    assert "SIM-MNT-2026-0917-118" in evidence
    assert "approved maintenance" in evidence.lower()


def test_invalid_scenario_returns_safe_catalogue_without_model(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(guardian, "_get_openai_client", lambda: fake_client)
    response = client.post("/chat", json={"message": "assess", "context": {"scenario_id": "unknown"}})
    assert response.status_code == 200
    assert "No mock SLA scenario matches" in response.json()["response"]
    assert not fake_client.chat.completions.calls


def test_custom_console_exposes_safe_left_panel_without_hidden_reasoning():
    response = client.get("/console")
    assert response.status_code == 200
    assert "Development steps" in response.text
    assert "not private model reasoning" in response.text
    assert "grid-template-columns:300px" in response.text

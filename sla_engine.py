"""Read-only Enterprise SLA Guardian correlation and deterministic fallback reports."""

from __future__ import annotations

from typing import Any

from mock_data import SCENARIOS, scenario_data, scenarios


class ScenarioNotFound(ValueError):
    """Raised when a request explicitly selects an unknown simulation scenario."""


def select_scenario(message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Select one mock scenario only; this agent never queries production systems."""
    context = context or {}
    requested = str(context.get("scenario_id", "")).strip().lower()
    if requested:
        if requested not in SCENARIOS:
            raise ScenarioNotFound(f"No mock SLA scenario matches `{requested}`.")
        return scenario_data(requested)

    text = message.lower().replace("_", "-")
    if any(term in text for term in ("maintenance", "exempt", "ethernet", "handoff")):
        return scenario_data("planned-maintenance-degradation")
    if any(term in text for term in ("5g", "private", "throughput", "factory", "congestion")):
        return scenario_data("private-5g-congestion-risk")
    return scenario_data("sdwan-latency-breach-risk")


def list_scenarios_report() -> str:
    """Return the explicit simulation catalogue without requesting the LLM."""
    lines = ["# Enterprise SLA Guardian — available simulations", ""]
    for item in scenarios():
        lines.append(
            f"- **{item['scenario_id']}** — {item['title']} "
            f"(`{item['incident_id']}`, {item['service_domain']})"
        )
    lines.extend(
        [
            "",
            "Use `context.scenario_id` to select a scenario. All scenarios contain synthetic, de-identified data.",
            "",
            "## Safety boundary",
            "This is a read-only simulation. No customer communication, SLA classification, service-credit commitment, ticket operation, escalation, or network change has been performed.",
        ]
    )
    return "\n".join(lines)


def build_sla_report(scenario: dict[str, Any]) -> str:
    """Produce a complete non-generative fallback for provider outages."""
    maintenance = scenario["maintenance"]
    services = scenario["services"]
    lines = [
        "# ENTERPRISE SLA GUARDIAN — READ-ONLY ADVISORY",
        "",
        "## SLA risk assessment",
        f"**Simulation:** {scenario['id']} — {scenario['title']}",
        f"**Assessment time:** {scenario['assessment_time']}",
        f"**Trigger:** {scenario['trigger']}",
        f"**Risk posture:** {'Maintenance-exempt pending post-window validation' if maintenance['approved_overlap'] else 'Contractual exposure requires human review'}",
        "",
        "## Telemetry and service-path evidence",
        f"- **Observation window:** {scenario['telemetry']['window']}",
        f"- **Trend:** {scenario['telemetry']['pattern']}",
        f"- **Projection:** {scenario['telemetry']['trend']}",
        f"- **Confidence:** {scenario['telemetry']['confidence']}",
        f"- **Service path:** {scenario['service_path']['path']}",
        f"- **Suspected domain:** {scenario['service_path']['suspected_domain']}",
        f"- **Maintenance context:** {maintenance['status']}",
        f"- **Related problem:** `{scenario['related_problem']['id']}` ({scenario['related_problem']['status']}) — {scenario['related_problem']['summary']}",
        "",
        "## Customer and contractual exposure",
        "| Customer | Service | Tier | Contract | Observed condition | Exposure |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for service in services:
        lines.append(
            f"| {service['customer']} | `{service['service_id']}` — {service['service_name']} | "
            f"{service['tier']} | {service['contract']} | {service['observed']} | {service['exposure']} — {service['risk']} |"
        )

    lines.extend(["", "## Recommended operator-controlled actions"])
    lines.extend(f"1. {action}" for action in scenario["recommended_actions"])
    lines.extend(["", "## Draft customer communication guidance"])
    for service in services:
        lines.append(
            f"- **Draft only — {service['customer']}:** Acknowledge the observed condition for "
            f"`{service['service_id']}`, state the current investigation status, and provide an approved next-update time. "
            "Do not state an unconfirmed root cause, a breach classification, restoration commitment, or service credit."
        )
    lines.extend(["", "## Approval gates"])
    lines.extend(f"- {gate}" for gate in scenario["approval_gates"])
    lines.extend(
        [
            "",
            "## Safety boundary",
            "This is a read-only simulation. No customer communication, SLA classification, service-credit commitment, ticket operation, escalation, or network change has been performed.",
        ]
    )
    return "\n".join(lines)

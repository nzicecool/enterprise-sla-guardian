"""De-identified, deterministic Enterprise SLA Guardian simulation data.

All values are synthetic and solely intended for Agent Manager demonstrations.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

SCENARIOS: dict[str, dict[str, Any]] = {
    "sdwan-latency-breach-risk": {
        "id": "SLA-SIM-2026-0917-001",
        "title": "Enterprise SD-WAN latency trending toward a contractual breach",
        "assessment_time": "2026-09-17T02:10:00Z",
        "trigger": "Predicted latency-threshold breach from the service-assurance rule set",
        "service_domain": "Managed SD-WAN",
        "maintenance": {
            "approved_overlap": False,
            "status": "No approved maintenance overlaps the degradation window.",
        },
        "related_problem": {
            "id": "SIM-SP-2026-0917-042",
            "status": "Investigating",
            "summary": "Elevated transport latency on the Bangkok–Singapore transit path.",
            "evidence_link": "mock://problems/SIM-SP-2026-0917-042",
        },
        "service_path": {
            "path": "BKK-PE-03 → TH-Transit-02 → SG-Core-01",
            "suspected_domain": "Transport transit segment TH-Transit-02",
            "change_context": "No approved routing or maintenance change in the affected interval.",
        },
        "telemetry": {
            "window": "Last 45 minutes",
            "pattern": "p95 round-trip latency rose from 47 ms to 79 ms; packet loss rose from 0.08% to 0.43%.",
            "trend": "The current slope projects a p95 latency threshold breach in approximately 35 minutes if unchanged.",
            "confidence": "High: three successive five-minute windows show the same direction of travel.",
        },
        "services": [
            {
                "customer": "Meridian Capital Thailand",
                "service_id": "SIM-SDWAN-MCT-014",
                "service_name": "Treasury and branch SD-WAN",
                "tier": "Platinum",
                "contract": "p95 latency ≤ 80 ms; packet loss ≤ 0.50%; 99.95% monthly availability",
                "observed": "p95 latency 79 ms and rising; packet loss 0.43%",
                "risk": "Imminent latency breach",
                "window": "Business-critical processing window: 02:00–10:00Z",
                "exposure": "High",
            },
            {
                "customer": "Atlas Manufacturing Industries",
                "service_id": "SIM-SDWAN-AMI-031",
                "service_name": "Factory and regional-office SD-WAN",
                "tier": "Gold",
                "contract": "p95 latency ≤ 120 ms; packet loss ≤ 1.00%; 99.90% monthly availability",
                "observed": "p95 latency 103 ms; packet loss 0.31%",
                "risk": "Watch: within contract, but shares the affected transit path",
                "window": "24×7 service window",
                "exposure": "Moderate",
            },
            {
                "customer": "Northstar Retail Network",
                "service_id": "SIM-SDWAN-NRN-009",
                "service_name": "Point-of-sale SD-WAN",
                "tier": "Standard",
                "contract": "p95 latency ≤ 150 ms; packet loss ≤ 1.50%; 99.50% monthly availability",
                "observed": "p95 latency 97 ms; packet loss 0.27%",
                "risk": "Monitor: no current contractual exposure",
                "window": "Retail operating window: 00:00–14:00Z",
                "exposure": "Low",
            },
        ],
        "recommended_actions": [
            "Validate the latency increase independently at BKK-PE-03 and SG-Core-01 using existing read-only telemetry views.",
            "Ask the transport incident commander to confirm the condition and the next approved investigation checkpoint for SIM-SP-2026-0917-042.",
            "Prioritize Meridian Capital Thailand for an account-manager review because its Platinum latency threshold is projected to breach first.",
            "Prepare, but do not send, a fact-based service-status draft that states the observed trend, current investigation status, and next update time.",
        ],
        "approval_gates": [
            "Account or service manager approval before any customer communication.",
            "Contract owner approval before classifying an SLA breach or promising a service credit.",
            "Incident commander approval before executive escalation or any production-network change.",
        ],
    },
    "planned-maintenance-degradation": {
        "id": "SLA-SIM-2026-0917-002",
        "title": "Managed Ethernet degradation inside an approved maintenance allowance",
        "assessment_time": "2026-09-17T03:25:00Z",
        "trigger": "Service-quality alert during an approved maintenance window",
        "service_domain": "Managed Ethernet",
        "maintenance": {
            "approved_overlap": True,
            "status": "SIM-MNT-2026-0917-118 is approved from 03:00Z to 04:00Z and includes the affected access handoff.",
        },
        "related_problem": {
            "id": "SIM-SP-2026-0917-051",
            "status": "Monitoring",
            "summary": "Expected packet-loss increase during approved handoff replacement.",
            "evidence_link": "mock://problems/SIM-SP-2026-0917-051",
        },
        "service_path": {
            "path": "BKK-ME-14 → Access-Ring-7 → DC-Edge-02",
            "suspected_domain": "Approved access handoff replacement",
            "change_context": "The telemetry aligns with the approved maintenance scope and time window.",
        },
        "telemetry": {
            "window": "Last 20 minutes",
            "pattern": "Packet loss is 1.8%; p95 latency is 66 ms, up from 31 ms.",
            "trend": "The effect is bounded to the approved window; no post-maintenance recovery evidence is available yet.",
            "confidence": "High: matching maintenance identifier, path, and maintenance period.",
        },
        "services": [
            {
                "customer": "Banyan Health Services",
                "service_id": "SIM-ME-BHS-022",
                "service_name": "Primary data-centre Ethernet",
                "tier": "Platinum",
                "contract": "p95 latency ≤ 70 ms; packet loss ≤ 0.75%; approved maintenance exclusion applies",
                "observed": "p95 latency 66 ms; packet loss 1.8% during approved maintenance",
                "risk": "Operational watch; verify recovery after the stated window",
                "window": "24×7 service window",
                "exposure": "Maintenance-exempt pending validation",
            },
        ],
        "recommended_actions": [
            "Confirm that the work remains within the approved maintenance scope and document the latest customer-impact status.",
            "Schedule a post-window service validation at 04:00Z before deciding whether an SLA investigation is needed.",
            "Prepare an informational maintenance-status draft only if the account manager requests one.",
        ],
        "approval_gates": [
            "Contract owner approval before treating this event as a non-exempt SLA breach.",
            "Account-manager approval before sending any customer update.",
            "Change-manager approval before modifying the maintenance plan or schedule.",
        ],
    },
    "private-5g-congestion-risk": {
        "id": "SLA-SIM-2026-0917-003",
        "title": "Private 5G factory service approaching throughput and latency commitments",
        "assessment_time": "2026-09-17T04:40:00Z",
        "trigger": "Concurrent throughput and latency degradation on a premium private 5G service",
        "service_domain": "Private 5G",
        "maintenance": {
            "approved_overlap": False,
            "status": "No approved radio, core, or transport maintenance overlaps the event.",
        },
        "related_problem": {
            "id": "SIM-SP-2026-0917-059",
            "status": "Assigned",
            "summary": "Private 5G core-user-plane congestion under investigation.",
            "evidence_link": "mock://problems/SIM-SP-2026-0917-059",
        },
        "service_path": {
            "path": "Factory-RAN-04 → P5G-UPF-BKK-02 → Enterprise edge",
            "suspected_domain": "Private 5G user-plane capacity",
            "change_context": "No matching approved change is recorded.",
        },
        "telemetry": {
            "window": "Last 30 minutes",
            "pattern": "Median uplink throughput declined from 86 Mbps to 58 Mbps; p95 latency increased from 24 ms to 44 ms.",
            "trend": "The trend threatens the premium latency objective in the next service-quality evaluation window.",
            "confidence": "Medium: radio utilisation and user-plane queue depth correlate, while the upstream cause remains unconfirmed.",
        },
        "services": [
            {
                "customer": "Orchid Precision Components",
                "service_id": "SIM-P5G-OPC-004",
                "service_name": "Factory automation private 5G",
                "tier": "Premium",
                "contract": "p95 latency ≤ 45 ms; median uplink throughput ≥ 60 Mbps; 99.95% monthly availability",
                "observed": "p95 latency 44 ms; median uplink throughput 58 Mbps",
                "risk": "Imminent dual-metric breach",
                "window": "Production window: 04:00–12:00Z",
                "exposure": "High",
            },
        ],
        "recommended_actions": [
            "Validate the queue-depth and throughput trend from the approved read-only private-5G dashboards.",
            "Coordinate with the owner of SIM-SP-2026-0917-059 for a confirmed investigation timeline.",
            "Prepare a premium-customer status draft that distinguishes the observed condition from any unconfirmed root cause.",
        ],
        "approval_gates": [
            "Account-manager approval before sharing a customer status draft externally.",
            "Contract owner approval before declaring a committed-objective breach or offering compensation.",
            "Network change-control approval for any capacity, routing, or radio configuration action.",
        ],
    },
}


def scenarios() -> list[dict[str, str]]:
    """Return compact public scenario metadata without internal prompt material."""
    return [
        {
            "scenario_id": key,
            "incident_id": item["id"],
            "title": item["title"],
            "service_domain": item["service_domain"],
        }
        for key, item in SCENARIOS.items()
    ]


def scenario_data(scenario_id: str) -> dict[str, Any]:
    """Return an isolated copy so the deterministic evidence cannot be mutated."""
    return deepcopy(SCENARIOS[scenario_id])

# Enterprise SLA Guardian

The **Enterprise SLA Guardian** is a model-backed, read-only demo agent for WSO2 Agent Manager. It evaluates **synthetic, de-identified** telemetry, contracted service objectives, maintenance windows, service paths, and open-problem context. It identifies customers at risk, explains the evidence, prioritizes human review, and produces draft-only customer communication guidance.

## Safety model

The agent does **not** query production systems and does **not** possess tools to send communications, change a ticket, declare a contractual breach, offer a service credit, escalate a customer, change capacity, or modify a network. Every response is anchored in one selected mock scenario. Customer updates, SLA classifications, commercial commitments, and operational changes remain human approval gates.

If the LLM cannot be reached, a deterministic report generated from the same mock evidence is returned instead. This makes the demo resilient without masking model availability.

## Simulated scenarios

| Scenario ID | Simulation | Purpose |
| --- | --- | --- |
| `sdwan-latency-breach-risk` | Platinum SD-WAN latency trending toward threshold | Tests early warning, exposure ranking, and draft customer communication guidance. |
| `planned-maintenance-degradation` | Managed Ethernet performance impact during approved work | Distinguishes a maintenance exclusion from an SLA breach. |
| `private-5g-congestion-risk` | Premium private 5G capacity and latency risk | Tests multi-metric risk assessment and account escalation preparation. |

Use `context.scenario_id` in `POST /chat` to select one of these scenarios. Without it, service-related keywords select a scenario and the SD-WAN risk scenario is the default.

## LLM providers and history

Gemini is the default because it is suited to a fast, grounded advisory experience. The runtime supports configurable providers through environment variables:

| Provider | `LLM_PROVIDER` | Protocol |
| --- | --- | --- |
| Gemini | `gemini` | OpenAI-compatible Chat Completions |
| Anthropic Claude | `anthropic` | Native Anthropic Messages API |
| OpenAI | `openai` | OpenAI-compatible Chat Completions |
| Z.ai / GLM | `glm` | OpenAI-compatible Chat Completions |

Set `LLM_MODEL`, `LLM_PROVIDER_URL`, `LLM_PROVIDER_KEY`, `LLM_MAX_TOKENS` (128–2048), and `LLM_HISTORY_MESSAGES` (0–12) for the chosen provider. The agent retains a bounded in-memory prompt history per `session_id` and never exposes a credential or hidden model reasoning. It supplies an auditable `development_steps` list with every chat response.

## Safe left-panel console

`GET /console` serves an optional responsive interface with an on-screen **Development steps** panel. It contains only safe workflow milestones, such as selecting approved mock evidence and applying approval constraints. It does not contain chain-of-thought or private model reasoning. Through Agent Manager, the endpoint remains protected by the agent API-key policy.

## Local verification

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=. .venv/bin/pytest -q
```

With a provider key available only in runtime environment variables, run `python main.py` and call `POST /chat`.

## Local Agent Manager Quick Start deployment

The repository deployment manifests have **references only**. From the repository root, pass the credential directly from a trusted environment variable into the script:

```bash
chmod 0755 deployment/apply_local_quickstart_llm.sh
printf '%s' "$OPENAI_API_KEY" | ./deployment/apply_local_quickstart_llm.sh
```

The script writes the key directly to OpenBao, applies the `SecretReference` and data-plane `ExternalSecret`, and appends secret-backed `ReleaseBinding` overrides. It never stores the credential in source, shell history, a command argument, or deployment manifests.

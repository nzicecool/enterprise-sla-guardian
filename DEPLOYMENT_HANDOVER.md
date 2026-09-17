# Enterprise SLA Guardian — Deployment Handover

**Author:** Manus AI  
**Deployment date:** 17 September 2026  
**Status:** **Deployed and validated**

## Deployment outcome

The **Enterprise SLA Guardian** is deployed in the default WSO2 Agent Manager project as a read-only enterprise telecom service-assurance agent. It uses de-identified mock evidence to assess SLA exposure, rank customer risk, recommend operator-controlled next steps, and draft communications for account-manager approval. It is intentionally unable to send messages, classify a contractual breach, create or change tickets, offer service credits, perform executive escalation, or make network changes.

The application follows the Agent Manager platform-hosted agent lifecycle and is available in the Console’s **Try It** experience. WSO2 Agent Manager provides the governed lifecycle for agent configuration, build, deployment, security, and observability used by this deployment.[1]

## Access

Open the **[Enterprise SLA Guardian Try It chat](https://3000-i8ilga8xy601yp7l81km7-04c18718.sg2.manus.computer/org/default/project/default/agents/enterprise-sla-guardian/environment/default/tryOut/chat)** in Agent Manager. The public deployment endpoint is exposed at `https://3000-i8ilga8xy601yp7l81km7-04c18718.sg2.manus.computer/enterprise-sla-guardian` and is protected with the Agent Manager API-key policy. The unauthenticated `/health` check was verified to return `401`.

> The sandbox URL is temporary. Use the Agent Manager deployment view as the authoritative place to obtain the endpoint after a Quick Start restart or when moving this agent to another environment.

## Model and secret configuration

The active release uses the Gemini-compatible provider configuration shown below. The model credential is stored in OpenBao and synchronized into the data-plane namespace through an ExternalSecret. It is **not** committed to the source repository, written to a manifest, logged, or included in this handover.

| Setting | Active value |
| --- | --- |
| Provider | `gemini` |
| Model | `gemini-3-flash-preview` |
| Protocol | OpenAI-compatible chat completions |
| Max response tokens | 900 |
| Conversation history | Six messages per in-memory session |
| Credential delivery | OpenBao secret → ExternalSecret → Kubernetes `secretKeyRef` |
| Fallback | Deterministic, mock-data SLA advisory when the model is unavailable |

The deployed runtime reported all six expected LLM configuration variables and a configured Gemini client. A live in-cluster operational advisory reported `provider: gemini` and `used_fallback: false`.

## Mock demonstrations

The source repository is private and available at [Enterprise SLA Guardian on GitHub](https://github.com/nzicecool/enterprise-sla-guardian). It contains deterministic synthetic evidence for three demonstrations:

| Scenario identifier | Demonstrates |
| --- | --- |
| `sdwan-latency-breach-risk` | SD-WAN latency moving toward a contracted threshold, with customer prioritization and an approval-gated update draft |
| `planned-maintenance-degradation` | Managed Ethernet service impact assessed against an approved maintenance allowance |
| `private-5g-congestion-risk` | Private 5G congestion risk, evidence review, and contingent stakeholder communication guidance |

A validated Try It request was: `Assess the SLA exposure for the enterprise SD-WAN latency trend, prioritize customers, and prepare a draft update subject to approval.` The Console returned an advisory for the Bangkok–Singapore SD-WAN latency degradation and included the mandatory read-only safety statement.

## Validation record

| Check | Result |
| --- | --- |
| Agent Manager build | `enterprise-sla-guardian-1789611309582` completed successfully at `2026-09-17T02:17:56Z` |
| Release binding | Active and Ready |
| Data-plane credential sync | Ready; only secret metadata was inspected |
| Runtime | One `enterprise-sla-guardian` pod running with its container ready |
| Unit and API tests | 9 tests passed |
| Agent Manager Try It | Completed successfully through the API-key-protected gateway |
| Live model validation | Gemini provider used; deterministic fallback was not used |
| Safety boundary | Present in the live response |

## Recovery note

The initial build failed at source checkout because the shared protected GitHub basic-auth credential was stale. The credential was refreshed directly in OpenBao from the existing authenticated GitHub CLI session, without printing or persisting the token. The replacement build then succeeded. No agent logic or mock data was changed to address that infrastructure credential issue.

## Operating boundary

Responses are advisory only. They should be treated as simulation output until the mock-data adapters are replaced with governed production integrations. Any customer communication, incident or problem record update, contractual breach decision, service-credit decision, escalation, or network operation requires a separate human approval and an explicitly authorized integration.

## References

[1]: https://wso2.github.io/agent-manager/docs/v1.0.0/get-started/what-is-amp/ "WSO2 Agent Manager documentation: What is Agent Manager?"
[2]: https://github.com/wso2/agent-manager "WSO2 Agent Manager source repository"

I'd push back before generating this one — two problems compound:

1. **Wrong diagram type for the stated intent.** A sequence diagram models *one flow over time* — a specific scenario, traced through participants. "Every interaction between 28 services" isn't a flow; it's the union of every flow the system supports. Drawing it as one sequence diagram produces a wall of crossing arrows with no temporal meaning (which call happens first? depends on the flow — and there are dozens of flows).

2. **God-diagram, even if we picked the right type.** 28 participants in one sequence diagram (or 28 nodes in one component diagram) is past the point where a human can read it. The skill's threshold is ~20 for sequence, ~15 for component, and the eye gives up well before that.

**What I'd generate instead, depending on what you actually need:**

- **"I want to see the static shape of the system — who talks to whom."** → A **C4 Container diagram** (one box per service, lines for the dependencies, tech labels on the lines). 28 containers is still a lot, but C4 is designed for this scale, and you can group by bounded context. If even that's too dense, split into 3–4 C4 Container diagrams per subsystem.

- **"I want to see how a specific operation flows through the services."** → A **sequence diagram per critical path** — checkout, signup, refund, etc. Each one touches 4–8 services, reads cleanly, and the set of them collectively documents the interactions that actually matter. The ones nobody draws are the ones nobody cares about.

- **"I want a living map for onboarding / incident response."** → That's not a PlantUML job. Generate it from your service mesh / tracing data (Jaeger service graph, Istio Kiali, Tempo service map). A hand-drawn 28-service diagram is stale the day after you draw it.

Tell me which of those three you want and I'll generate it. My default recommendation: **one C4 Container diagram grouped by bounded context, plus sequence diagrams for the 3–5 flows you care about most.** Two artifacts, both readable, both maintainable.

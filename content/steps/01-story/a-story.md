Most ticketing sites put buyers in a queue, both to prevent server crashes and
to manage high demand. You start your purchase and find yourself behind 14,000
people. The queue moves for forty minutes. When your turn finally comes, you
have a short window to pick seats and pay. If you miss that window, your place
in line is given away.

Many real-world tasks follow this pattern: a task that takes far longer than a
single conversation, running against an external system you do not control.
Examples include waiting for a supplier to restock, waiting for a claim
approval, or waiting in a queue.

Standard AI agents live inside a single chat turn, which lasts seconds and is
purely reactive. They cannot wait 40 minutes or act autonomously. To solve
this, you need a long-running agent: a system that stays dormant during long
waits, persists context across process restarts, and resumes automatically
when woken by an external trigger.

This workshop walks you through building a concert ticket queue agent, covering
the core architectural patterns required for long-running agents on Google
Cloud.

:::warn
**⚠️ ETHICAL DISCLAIMER:**
**Ticket bots are a real problem and real ticketing sites prohibit automation.** This workshop runs against a **mock venue service**, buying **one** allotment for **yourself**, inside limits you set.
:::

## What you'll build

:::figure src="/docs-img/overview.png" caption="What you are building"
:::

In this workshop, you will build a long-running ticket booking agent while learning key agentic software patterns:

- **Process Suspension & Resumption**: Park an agent invocation during long wait periods and resume execution via external triggers.
- **Durable State Storage**: Persist conversation state and artifacts across process restarts using SQLite/Cloud SQL and Cloud Storage.
- **Staleness Guards & Idempotency**: Verify dynamic data (like seat availability) before acting and use idempotency keys to prevent duplicate transactions.
- **ADK Workflow Graphs**: Structure execution using deterministic code nodes for procedural rules and agent nodes for contextual decision-making.
- **Human-in-the-Loop Approval**: Pause execution to collect and persist explicit spending limits from the user.
- **Cloud Deployment**: Containerize and deploy the agent to Cloud Run with Cloud Scheduler and Pub/Sub triggers.

## Scenario Overview

In this workshop scenario, your agent books two tickets for a concert ("The Midnight Signal" in Amsterdam). The user's preferences stored in historical memory include:
- Must be a weekend show (Sam cannot attend weeknights).
- Avoid upper bowl seating at Ziggo Dome (poor visibility).
- Target price is approximately $200 per ticket, with a $250 max limit.

:::figure src="/docs-img/poster.png" caption="The Midnight Signal, on tour"
:::

## The bench

The venue panel on the left is the control panel, your buttons. The ‹ at the
top of the column folds it away, and › brings it back.

Loading a step's code presses **RESET THE VENUE** for you.

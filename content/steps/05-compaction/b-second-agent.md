`budget_split` is a whole separate agent, not a tool:

:::code path="agent/concert/agent.py" highlight="^budget_split = |^\s+include_contents=|^\s+output_key=|AgentTool\(agent=budget_split"
:::

**Why an agent and not a plain function?** Because the work needs a model. Read "which of these sections fit a $200 budget for four people, and what is the total" as arithmetic wrapped in judgement, with an answer a person has to be able to read. Let a Python function multiply, and do not ask it to decide which options are worth mentioning.

**Then why not let the main agent do it?** Look at the next line `include_contents="none"` means this agent is handed **none** of the conversation. No group chat, no preferences, no forty tour dates. It gets the request and
nothing else. That flag only exists on an `Agent`, which is the real reason this is an agent rather than a function.

:::figure src="/docs-img/05-02-subagent.png" caption="A sub-agent that sees the request and nothing else"
:::

Prefer the short prompt: cheaper, faster, and much harder to derail. Rely on the arithmetic being immune to something said twenty turns ago, because it never sees it.

**Why `AgentTool`?** Wrap the agent with it so the main agent can call it like any other tool. From the model's side, read `budget_split` as identical to `search_events`.

**And `output_key="budget_plan"`** puts the answer into session state under that name instead of leaving it loose in the conversation. Watch why that matters.

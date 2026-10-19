LLMs are great at making decisions (like picking a show based on user preferences). But relying on an LLM to follow strict step-by-step rules (like "always join the queue before checking seats") means it will occasionally skip steps or mess up the order.

To fix this, split the workflow into two types of steps:

- **Fixed Rules (Code Functions)**: Steps that must happen the exact same way every time (taking a queue ticket, checking position) are written as ordinary code nodes.
- **Decisions (Agent Nodes)**: Steps requiring judgment (choosing seat sections, checking user preferences) are given to the AI agent.

**Look at what is actually in this flow.** Some of it has no judgement in it at
all:

| Step | Judgement? |
|---|---|
| take exactly one queue ticket | **no.** Always one, always before buying |
| check whether it is your turn | **no.** Ask, read the answer |
| write the brief for the buyer | **no.** Same sentence, same shape, every time |
| which show, which section | **yes.** Price, day, who is coming, what they hate |
| user perference and limitation | **yes.** |

Everything in the first group is a rule. Leaving a rule to a model means it is
followed *nearly* always, and at 3am nobody is watching the time it is not.

So **ADK's `Workflow` lets you make the fixed parts deterministic and keep an agent only where a decision genuinely needs one.** Rules become function nodes that run the same way every time. Judgement stays in agent nodes. The wait becomes a node that parks the run instead of sleeping through it.

**Your agent is not replaced by any of this.** It becomes the last node in that
graph, with every tool, callback and idempotency key intact. The graph decides
what happens and in what order. Your agent still does the buying.

What changed since the last step:

| File | What changed |
|---|---|
| `nightly.py` | new. The unattended run as an ADK 2 `Workflow` graph |
| `agent.py` | `root_agent` **is now the graph.** The agent you have been talking to is still there, renamed `buyer_agent`, and is one node inside it |
| `agent.py` | it also **lost `join_queue` and `check_queue`** — the graph owns the queue now |
| `fence.py` | new. Runs immediately before a purchase and can block it |
| `agent.py` | `before_tool_callback=refresh_before_purchase` |
| `tools.py` | `purchase` now sends an `Idempotency-Key` header |

Long-running agents store history, and history is not the same as truth. Time
passes while the agent waits, and the world moves on without telling it.

`fence.py` is a callback ADK runs in the moment before any tool call.

**Something you did not write is going to retry your purchase.** The order
commits, the response dies on the way back, and from where the agent stands a
successful purchase and a failed one look identical. So it tries again. In the
final step ADK's own Pub/Sub trigger does this for you
(`ADK_TRIGGER_MAX_RETRIES`, default 3); elsewhere it is a load balancer, a queue,
or a person clicking twice. ADK's `ResumabilityConfig` docstring says it plainly:

> *"Tool call to resume needs to be idempotent because we only guarantee an
> at-least-once behavior once resumed."*

**At-least-once means more than once, sometimes.** You cannot stop the retry, so
the venue has to be able to recognise it — and that means the second attempt has
to arrive carrying something the first one had.

:::exercise id="code"
Derive that key from the request itself, so a retry of the *same* purchase
produces the *same* key, while a genuinely different purchase produces a
different one:

:::code path="agent/concert/tools.py" highlight="hashlib\.sha256\(|tool_context\.session\.id\}|\x22Idempotency-Key\x22: key" button="false"
:::

:::code path="agent/concert/agent.py" highlight="^root_agent = nightly|^buyer_agent = Agent" button="false"
:::

Note that `adk web` executes whichever object is assigned to `root_agent`. Here, `root_agent` points to the `nightly` Workflow graph, with `buyer_agent` configured as the final node in the graph.
:::

:::warn
**`adk web` treats every folder under `agent/` as an app,** and if any one of them is not a valid agent package the whole dropdown fails to load. Running things from inside `agent/` can leave a stray `memory/` or `artifacts/` folder behind, which is enough to do it. `ls agent/` should show `concert/` and nothing else.
:::

:::exercise id="run"
:::

:::section headline="Why it stopped instead of waiting"
Here is the version nobody should write:

```python
# what NOT to write — this is nobody's file
while not ready:          # never do this
    time.sleep(1)
```

It keeps a process alive for forty minutes to achieve nothing, dies with the terminal, and cannot be resumed. Here is what `check_front` does instead:

:::code path="agent/concert/nightly.py" highlight="^def check_front|^\s+return RequestInput\(" button="false"
:::

`RequestInput` is an **interrupt**. The graph stops where it stands, the
invocation goes to the session store, and the process is free to exit.
:::

## Wake it up — and mind which box you type in

**There are now two places you can type, and they do different things.**

| Where you type | What happens |
|---|---|
| the **`Enter your response...`** box on the `adk_request_input` event | answers the interrupt. The parked run **continues** from `check_front` |
| the main chat box at the bottom | starts a **new** invocation. The graph replays from `START`, picks a show again, and takes a **second queue ticket** |

:::warn
**Use the box attached to the event, not the chat box at the bottom.** This is the difference between resuming a parked run and starting a new one, and the two look identical until you check the venue panel and find two tickets. Everything `rerun_on_resume` does depends on getting this right.
:::

```
[check_front] #14,197 — not yet. Pausing.
```

**One line.** It did not pick a second show and it did not take a second queue
ticket, which would have put you at the back of a queue of 14,203.

**The graph is fully green, and the edges are counted.** `brief` and `concert` have lit up — the two nodes that had never run. And the edges into `pick_show`,
`queue_up` and `check_front` now carry a badge.

**`2x` is the number of times the graph walked that edge, once per wake-up.** The 2 at the top are the price of resuming: the scheduler re-enters the graph from the beginning each time. It does *not* mean the work happened three times, and the venue panel is the proof: one queue ticket, not 2. `@node(rerun_on_resume=False)` is why.

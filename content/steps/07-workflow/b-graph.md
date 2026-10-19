:::figure src="/docs-img/08-02-workflow.png" caption="The graph: functions for rules, agents for judgement"
:::

:::exercise id="graph"
:::task id="graph-files"
:::

**Note that two nodes are agents and two are functions, and treat which is which as the whole design question.**

| Node | Why that shape |
|---|---|
| `pick_show` | **agent.** Choosing a show from someone's history is judgement. It calls `recall`, reads the tour, and returns a validated `Plan` |
| `queue_up` | **function.** Joining a queue is a rule. A rule should not be a coin flip at 3am |
| `check_front` | **function.** "Am I at the front" has one right answer and the venue has it |
| `buy_it` | **agent.** It is `buyer_agent` — what `root_agent` used to be, unmodified. Section A sold out during the wait — take B, take C, or take nothing? |

Look at the last node and find the agent you built. Not a copy, not a rewrite:

:::code path="agent/concert/nightly.py" highlight="from \.agent import buyer_agent" button="false"
:::

All of it comes along: every tool it has, the seat-map re-read in `fence.py`, the
idempotency key in `purchase`. There is only one of it.
:::

:::note
**An agent node cannot be first.** An agent responds to its input. Put one straight after `START` with no user message and it has nothing to respond to, and the run hangs with no error and no timeout. That is why the graph opens with `open_the_night`, a three-line function whose only job is to say the sentence a person would have said.
:::

:::key
The run costs nothing while it waits, and it ends in exactly one place:
tickets bought. It just might take all night and several wake-ups to get
there.
:::

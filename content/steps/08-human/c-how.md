Open `nightly.py` and read `agree_budget`. Make three things true together, and
expect the same failure when any one is missing: it asks forever.

:::code path="agent/concert/nightly.py" highlight="^def agree_budget|interrupt_id=ASK_BUDGET|interrupt_id=CONFIRM_BUDGET|answers = getattr\(ctx, \x22resume_inputs\x22"
:::

| | |
|---|---|
| `rerun_on_resume=True` | without it the node is treated as done and skipped |
| a **stable** `interrupt_id` | the default is a fresh UUID per run, so there is nothing to look the answer up by |
| `ctx.resume_inputs[id]` | where the answer lands. **Not** the return value of `RequestInput` — ADK iterates a node rather than sending into it |

:::file path="agent/concert/nightly.py" label="Show nightly.py"
:::

:::note
**This is the same primitive as the queue.** `check_front` returns a `RequestInput` because the venue is not ready. `agree_budget` returns one because a person has not answered. To the framework there is no difference: the run parks, costs nothing, and survives the process dying. One mechanism covers "waiting for the world" and "waiting for a human", which is most of what long-running means.
:::

:::key
The agreement came from the person, they confirmed it out loud, and it dies
with the conversation it was agreed in. A limit that outlives the reason for
it is not a limit any more — it is a default nobody remembers choosing.
:::

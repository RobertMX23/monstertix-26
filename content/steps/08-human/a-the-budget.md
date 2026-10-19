An autonomous agent running overnight shouldn't make expensive financial choices based on guessed or ambiguous preferences from chat history.

Before executing high-stakes actions (like spending money on tickets), the agent must pause, ask the user to confirm their budget out loud, and save that explicit confirmation before making any purchases.

What changed since the last step:

| File | What changed |
|---|---|
| `budget.py` | Holds what the person agreed, as the sentence they said. `load()` reads it out of state, and `someone_is_there()` answers whether anybody is around to be asked |
| `agent.py` | the buyer's instruction now reads the agreed budget from the message it is sent |
| `tools.py` | added `set_budget`, so the agent can write an agreed limit into session state once a person has confirmed it |
| `nightly.py` | a new first node, `agree_budget`, which asks and reads back before anything else runs. It captures the budget **and** the rest of the ask, both as free text, and `SEATS` as a constant is gone |

:::exercise id="code"
## Don't model it. Store the sentence.

:::code path="agent/concert/budget.py" highlight="^def load\("
:::

```
state["budget"] = "up to $100 for the upper bowl or general admission, up to
                   $250 for the lower bowl, and up to $300 for a Saturday show"
```

The node checks two things... that **the person said it**, and that **they confirmed it**.

Then it keeps the sentence in session state rather than under `user:`, on purpose. A budget is agreed for one booking. "$250 if they're the good ones" was said about that band, on that night, and it has no business governing ticket booking.

## The same is true of everything else they said

Do not stop at the budget. People change their minds while they are deciding, so
capture everything they ask for here rather than relying on what the agent
happens to remember.

```
"I live in NYC, I can only do weekends, I have 10 people coming with me"
```

:::code path="agent/concert/nightly.py" highlight="^def what_they_asked_for"
:::

Read **Only events the user authored** it looks at **Only `text` parts** from the `function_response`, so the budget question and answer do not get echoed back in here. **No duplicates**.

Note `agree_budget` calls it on **every** run, not just the first, so a correction typed while the agent is queueing lands too. Then  `open_the_night` hand the picker both sentences, the ask and the budget, and the
picker read them.
:::

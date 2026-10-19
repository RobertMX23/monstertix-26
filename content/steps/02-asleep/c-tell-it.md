What would you do to fix it? Try the thing most people reach for first. Recall `INSTRUCTION`, the prose handed to the model on every turn, and rewrite it.

Open `agent/concert/agent.py`. Below `INSTRUCTION` there is a second one, already written for you. Try changing it yourself if you like:

:::code path="agent/concert/agent.py" highlight="^PROACTIVE_INSTRUCTION = \x22\x22\x22|Monitor the presale|Keep checking until"
:::
:::code path="agent/concert/agent.py" highlight="^root_agent = Agent\(|^    instruction=INSTRUCTION," button="false"
:::

:::exercise id="lab"
:::

It will agree, and it will sound like it means it.

Now wait. Do not type anything else. Watch the panel.

Give it a minute. **NOTHING HAPPENS!**

## Why that prompt was never going to work

Read it again with fresh eyes. *Monitor.* *The moment it opens.* *Keep checking.* Every one of those describes something happening **over time**.

Now recall what `instruction=` actually is. It is a string, handed to the model as part of the request, **at the moment somebody sends a message**. Nothing reads it in between turns.

```python
# agent/concert/agent.py
root_agent = Agent(
    instruction=PROACTIVE_INSTRUCTION,   # read on invocation
    ...                                  # ...and there was no invocation
)
```

An instruction cannot invoke the function it is written inside.

## Prompt Variations That Fail

Attempting to enforce autonomous execution via prompt instructions fails regardless of wording. Common prompt attempts—such as:

- *"Set a timer for 10:00 Tuesday and buy the tickets then."*
- *"Check every five minutes whether the presale has opened."*
- *"Act autonomously without waiting for user input."*

All fail for the same reason: prompts are read only when an invocation occurs. Without an external caller, no code is executed between turns.

:::note
**Prompting Limitations.** Prompts cannot schedule future execution. Even if a model responds that it will monitor a queue or run later, no active process or background timer is created.
:::

:::key
To make an agent autonomous, something outside the agent has to wake it up and call it.
:::

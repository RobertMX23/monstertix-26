A prompt is just text passed to an AI model when a call happens. It can't run on its own, wake itself up, or start a new call.

If you tell an agent in its prompt to "check back in 10 minutes," nothing actually happens after the current turn ends. The model has no internal clock or loop. To make an agent autonomous, something outside the agent has to wake it up and call it.

:::figure src="/docs-img/step2-overview.png" caption="Where this step sits"
:::

## Start the rig

We'll start by testing the developer tooling. **`adk web`** starts the **ADK web UI**, the development interface that ships with ADK. It lets you talk to the agent you are building without writing a frontend first, and it shows you what a chat window cannot show, such as every tool call and its arguments, the session state as it changes, the artifacts the agent saved, and the raw events underneath. You would not expose it in production. It is the best window into a running agent while you are learning. In step 3 you build the frontend you would actually expose, and in the final step you deploy it.

What you start with:

| File | What it is |
|---|---|
| `agent.py` | the agent — a name, a model, an instruction, a list of tools |
| `tools.py` | `search_events`, `get_seatmap` and `purchase` |
| `venue.py` | an HTTP client for the venue. Nothing interesting |
| `config.py` | which model to use, and a check that your credentials work |

## Talk to it

:::exercise id="run"
:::

It searches the tour, reads seat maps, and reasons about your budget and your company. This is a genuinely capable assistant.
However, when the presale opens at 10:00, the agent does not execute automatically because no process or background trigger is running.

## Read what just happened

The middle of the screen is not only a chat log. Every step of the turn is numbered, tool calls included:

```
  ▸ I want to see The Midnight Signal. I'm in Amsterdam...   ← user input
  ⚡ search_events({"city": "Amsterdam"})                     ← tool execution
  ✓ search_events                                            ← venue API response
    Two Amsterdam shows: Tuesday 10 Nov and Saturday 14 ...   ← model response
```

The tour information is not present in the model's training data or prompt. The agent retrieved this data by executing the `search_events` tool, which queried the venue API.

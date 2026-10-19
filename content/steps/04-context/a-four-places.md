If you put information in the wrong place:

- **It disappears too soon**: Important details get wiped out when the chat ends.
- **It sticks around too long**: Temporary facts contaminate long-term memory and confuse future conversations.

You need to match each piece of information to the right storage place and lifetime.

:::exercise id="code"
## The three tools we added

:::figure src="/docs-img/04-02-impl.png" caption="The three tools, and where each one writes"
:::

:::task id="files"
:::

**`note_companion`** records who is coming and what limits them:

:::code path="agent/concert/tools.py" highlight="^def note_companion|state\[\x22user:prefs\x22\] ="
:::

Add it because "Sam can't do weeknights" has to still be true next week. Write it into `user:prefs` to make that happen, and watch the `user:` part of the name do the work. Come back to that below.

**`recall` and `remember`** read and write a text file, `memory/userx.md`. Hold those for a moment.

Now look at the two places agent store it's context:

| location | What it holds |
|---|---|
| **State** | this session's memory, as key/value pairs — you live here in step 4 |
| **Artifacts** | files the agent saved, which never enter the prompt |

**Look at what changed in `get_seatmap`.** It used to return the whole seat map. Now it saves the seat map to a file and returns a short summary:

:::code path="agent/concert/tools.py" highlight="^async def get_seatmap|^def get_seatmap|save_artifact\(|state\[\x22temp:seatmap\x22\] ="
:::

Here is why that change matters.

Every tool return payload is appended to the conversation history and re-sent to the model on all subsequent turns. Returning large JSON objects (such as a 6 KB seat map) increases token consumption on every subsequent turn.

Save it to a file instead and pay one filename. Let the agent ask for the detail back with `load_artifact` if it needs it, and expect that most of the time it never will.

## Where the file goes: the artifact service

Look at the line in `get_seatmap` again, in `agent/concert/tools.py`:

:::code path="agent/concert/tools.py" highlight="save_artifact\("
:::

`tool_context` comes from ADK, which passes it into your tool as an argument, and `save_artifact` is a method on it. That line is where your tool hands the bytes to ADK.

ADK then writes them, using whichever **artifact service** it was started with. You picked that with the flag:

```bash
--artifact_service_uri="file://$WORKSHOP/artifacts"
```

ADK has three locations to store them:

| URI | Where the bytes go |
|---|---|
| `memory://` | RAM. Gone when you stop the process. This is the default if you pass no flag |
| `file://…` | a folder on disk. What you are using now |
| `gs://bucket` | Cloud Storage. What the deployed agent uses in the last step |

To move from your laptop to Cloud Storage, change `file://` to `gs://`. (We'll see this in Step 9)
:::

What changed since the last step:

| File | What changed |
|---|---|
| `tools.py` | added `note_companion`. `get_seatmap` now saves the seat map to a file |
| `memory.py` | new. Our own memory store |
| `agent.py` | three more tools in the list, and the instruction tells the agent to use them |

From step 4 on, the agent's switch starts it like this:

```bash
adk web agent --port 8000 --allow_origins "*" \
  --session_service_uri="sqlite+aiosqlite:///$WORKSHOP/sessions.db" \
  --artifact_service_uri="file://$WORKSHOP/artifacts"
```

:::figure src="/content-images/adk-storage.svg" caption="Where ADK now writes what happens in a session"
:::

Two flags you have not used before:

| Flag | What it is |
|---|---|
| `session_service_uri` | ADK writes every message, tool call and state change into it as rows (SQLite database.) |
| `artifact_service_uri` | Files the agent saves to.(Files) |

Without them, ADK keeps everything in memory and throws it away when you stop the process. These two settings are what make it persist.

The database `sessions.db` contains a seeded past conversation (`two-days-ago`) with 13 recorded events:

```
you    We're thinking about seeing The Midnight Signal. Me, Sam, and maybe Priya.
you    Sam can't do weeknights though, bailed on every single one.
you    Priya's out, she's away that weekend. Just me and Sam.
agent  Two it is. Still Saturday the 14th, still Amsterdam.
you    You said the upper bowl at Ziggo was bad last time?
```

**A memory file from three past bookings**, `memory/userx.md`, which you can open
in an editor:

```
- Sam bails on weeknights. Every weeknight show we booked, Sam cancelled.
- Hates the upper bowl at Ziggo Dome, "couldn't see a thing" from section B.
- Comfortable spend is around $200 per ticket. $250 is the hard ceiling.
- Always books two seats, always together.
```

**That is why the amber weeknight rows matter.** A weeknight show is $10 a seat cheaper, has better seats left, and sits at the top of the list, and it is the wrong answer for this person. The only reason the agent can know that is a file it wrote after the last booking. Whether that fact survives is steps 4 and 5.

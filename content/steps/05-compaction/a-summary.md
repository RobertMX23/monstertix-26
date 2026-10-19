When a conversation gets too long, the system summarizes older messages to save space and tokens.

Summaries are good for catching the general gist, that are good to save some token usage.

:::figure src="/docs-img/05-02-intro.png" caption="Compaction works on the session. Memory is a separate store"
:::

What changed since the last step:

| File | What changed |
|---|---|
| `agent.py` | the agent is wrapped in an `App`, with compaction switched on. A second agent, `budget_split`, does ticket arithmetic |
| everything else | unchanged |

:::exercise id="code"
`agent.py` no longer ends with `root_agent`. It ends with this:

:::code path="agent/concert/agent.py" highlight="^app = App\(|EventsCompactionConfig\(|compaction_interval=|overlap_size="
:::

Know that `adk web` looks for a variable called `app` first and falls back to
`root_agent`. Wrap the agent in an `App` whenever you need something that applies
to the whole application rather than to one agent: compaction here, and
resumability two steps from now.

**`compaction_interval=3`** means ADK summarises after every three turns. One
turn is you saying something and the agent finishing its reply, however many tools
it called along the way. Three is small so it fires during a workshop. A real app
would use a much larger number.

**`overlap_size=1`** means each summary starts one turn earlier than it strictly
needs to.

ADK summarises turns 1, 2 and 3. Three turns later it summarises the next
batch. With `overlap_size=1` that second summary starts at turn 3 again, not
turn 4:

:::figure src="/docs-img/05-02-compaction.png" caption="Two summaries, overlapping by one turn"
:::

Notice turn 3 gets summarised twice. That is deliberate. If you asked a question
in turn 3 and the agent answered in turn 4, a clean split puts the question in one
summary and the answer in the other, and leaves both confusing. Repeating a turn
is cheap insurance against cutting a thought in half.

Set both fields. ADK has no default for either.
:::

## Compaction and your memory service never meet

Worth being explicit, because the two words sound related and the systems are not.

`EventsCompactionConfig` is set on the **`App`** in `agent.py`, next to
`root_agent`. It is a property of the application, not of any service:

:::code path="agent/concert/agent.py" highlight="^app = App\(|EventsCompactionConfig\(|compaction_interval=|overlap_size="
:::

Nothing in that block mentions memory, and nothing in `memory.py` mentions
compaction. **A summary rewrites the conversation. It does not rewrite the file.**

That is the whole reason `remember()` exists as a deliberate call. Anything left
in the transcript is eventually read as a paraphrase somebody else wrote;
anything written to the file is read exactly as it was stored, tomorrow and next
week. The end of this step is where you watch that difference land.

## Where the summary is actually kept

In `sessions.db`, in the **`events`** table — the same table as every other turn.
A compaction record is not a separate store or a separate file. It is one more
event row, written by the agent, with a timestamp like any other.

What makes it different is where the text sits. An ordinary event carries a
`content` field. This one does not: its summary lives under `actions.compaction`.

```bash
sqlite3 sessions.db \
  "select json_extract(event_data,'\$.actions.compaction.compacted_content.parts[0].text')
   from events where event_data like '%compaction%';"
```

The shape, once you pull it apart:

```
events row
└── event_data  (JSON)
    ├── id, author, timestamp, invocation_id      ← like every other event
    ├── content                                    ← ABSENT on this one
    └── actions
        └── compaction
            ├── start_timestamp                    ← the window it replaced
            ├── end_timestamp
            └── compacted_content.parts[0].text    ← the summary itself
```

The event stream draws each event from its content. The summary is right there in the database, being sent to the model on every turn.

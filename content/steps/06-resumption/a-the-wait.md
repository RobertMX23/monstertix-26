When an agent has to wait in a 40-minute ticket queue, keeping a Python process alive and waiting is fragile and expensive.

To handle long waits properly:
1. **Save state to a database**: Store where the agent paused so the process can safely shut down.
2. **Wake up on demand**: When the wait is over, an external signal restarts the agent and resumes execution right where it left off.

What changed since the last step:

| File | What changed |
|---|---|
| `tools.py` | added `join_queue` and `check_queue` |
| `agent.py` | `join_queue` is wrapped in `LongRunningFunctionTool`, and the `App` turns on `ResumabilityConfig` |

`join_queue` returns straight away with a ticket instead of blocking, and
`ResumabilityConfig` lets the run pause on it and pick up afterwards.

:::figure src="/docs-img/06-02-intro.png" caption="What resumability adds"
:::

:::exercise id="code"
:::

## Run it

:::exercise id="run"
:::

Stop on two things in that answer.

Notice it picked **Saturday** without asking you. There are two Amsterdam shows, the 10th is a Tuesday, and the memory file from the last step says Sam does not do weeknights. That is a fact from a previous booking deciding a question in this one.

Notice too that it joined the queue **before** looking at a single seat or price, and said nothing about either. That is the venue's rule, you buy the tickets until they reach the front, so the only thing worth having early is a place in line. Which seats to take is a question for forty minutes from now.

The queue is genuinely forty minutes long and it is not going anywhere while you
work.

:::note
**Venue Speed Multiplier.** The speed multiplier determines how fast the queue is processed (default **1×**). Use **SKIP THE WAIT** to move to the front immediately, or set the speed to **60×** to accelerate processing. The agent code behaves identically regardless of clock speed.
:::

**Compare the ticket, and watch the position keep dropping while nothing was running.** Notice the agent did not know it had been killed. It called `check_queue` with the ticket it got before the restart, because that ticket was on disk.

:::terminal
sqlite3 sessions.db "select name from pragma_table_info('events');"
sqlite3 sessions.db "select event_data from events;" \
  | grep -o '"ticket": "q_[a-z0-9]*", "position": [0-9]*' | tail -1
:::

Six of the coloumns are labels. Every turn of every conversation is one row, and the turn itself, who said it, which tool it called, what came back,
is JSON inside `event_data`.

**That is the whole trick.** The ticket the venue gave you went to disk the moment `join_queue` returned, and killing the process did not touch it. When `adk web` came back it read these rows and handed the model the same conversation it had before, ticket included. So watch the agent carry on without ever knowing it had been dead.

**And notice what it did not do: start over.** It did not search the tour again, and it did not join the queue a second time. The events on disk record not just what was said but *where the run had got to* — parked on a `LongRunningFunctionTool` that had returned a ticket and was waiting on the queue. `ResumabilityConfig` is what makes that position part of the record rather than something living only in the dead process's memory, so the run picks up at that tool instead of replaying everything before it.

That distinction matters more than it looks. Replaying would mean a second `join_queue` call, a second ticket, and a place at the back of a queue of 14,203 people — the run would get further from finishing every time it was resumed.

:::note
**There is no `author` column.** In ADK 2.6.2 the events table is deliberately thin: identifiers, a timestamp, and one `event_data` blob. Everything else lives inside the JSON. If you want to query by author, pull it out with `json_extract(event_data, '$.author')`.
:::

:::figure src="/docs-img/06-02-timeline.png" caption="The same ticket, across a process that died"
:::

## Why `join_queue` and not `check_queue`

Both functions return in milliseconds. Only one of them is long-running, and the
difference is not how long the call takes — it is whether the **work** is
finished when the call returns.

| | what it returns | is the work done? |
|---|---|---|
| `join_queue` | a ticket, and position 14,203 | **no.** You are queued, not at the front. Forty minutes of it are still ahead |
| `check_queue` | a position, right now | **yes.** You asked a question, you got the answer |

`join_queue` hands back a *handle to something still in progress*. That is
exactly what `LongRunningFunctionTool` models: the tool returns, the work carries
on somewhere else, and the run is allowed to pause on it.

`check_queue` is a complete question with a complete answer. There is nothing
pending to wait for, so there is nothing to park on.

**And wrapping it would actively break the step.** If `check_queue` were long-running,
the run would park every time the agent asked where it was in line — including
when the answer is *"you are at the front, buy now"*. You would have built an
agent that suspends itself at the exact moment it should act.

:::figure src="/docs-img/06-02-aync.png" caption="Which call is still outstanding when it returns"
:::

## What made that work

Three separate things, and it is worth being clear about which does what, because they are easy to confuse.

:::code path="agent/concert/agent.py" highlight="^\s+LongRunningFunctionTool\(func=join_queue\)|resumability_config=ResumabilityConfig" button="false"
:::
```bash
--session_service_uri="sqlite+aiosqlite:///$WORKSHOP/sessions.db"
```

| | Job | Take it away and |
|---|---|---|
| `LongRunningFunctionTool` | lets `join_queue` hand back a ticket without the call being finished, so the invocation has something to wait on | `join_queue` becomes an ordinary tool. It returns the ticket, the agent reads it as a final answer and replies, and the turn ends. Nothing is waiting, so there is nothing to come back to |
| `ResumabilityConfig` | lets ADK park an invocation on that unfinished call and continue it later, from the last event | the tool still returns early, but the run cannot be suspended and resumed. There is no paused invocation to continue |
| the session URI | puts the session somewhere a new process can read | see below — this one is not what you expect |

:::note
**Read ADK's own docstring for `ResumabilityConfig`:**

*"1. pause an invocation upon a long-running function call. 2. resume an invocation from the last event, if it's paused or failed midway through. Note: ADK resumes in a best-effort manner: 1. Tool call to resume needs to be idempotent because we only guarantee an at-least-once behavior once resumed. 2. Any temporary / in-memory state will be lost upon resumption."*
:::

:::key
The agent was not running for those forty minutes. Something outside it
noticed the wait was over and started it again.
:::

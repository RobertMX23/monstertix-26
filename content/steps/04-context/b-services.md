:::figure src="/docs-img/04-02-contextmgnt.png" caption="Memory as an interface, with a file behind it"
:::

ADK gives you an interface for long-term memory called `BaseMemoryService`. It has two methods:

```python
# google.adk.memory.BaseMemoryService — ADK's interface, not your file
async def add_session_to_memory(session)                   # take a conversation in
async def search_memory(*, app_name, user_id, query)       # hand memories back
```

ADK ships three implementations of it:

| Class | URI | What it needs |
|---|---|---|
| `InMemoryMemoryService` | `memory://` | nothing. Loses everything when you stop the process |
| `VertexAiRagMemoryService` | `rag://` | a Vertex AI RAG corpus |
| `VertexAiMemoryBankService` | `agentengine://` | an Agent Engine resource |

We write our own for this workshop. Rule out `InMemoryMemoryService`, which forgets everything when you stop the process, and rule out the other two, which need cloud resources that take minutes to create. Pick a file instead, because you can seed it in advance and read it in an editor. So take `memory.py` as your own implementation, we're storing everything in a Markdown file:

:::code path="agent/concert/memory.py" highlight="^class MarkdownMemoryService|async def search_memory|async def add_session_to_memory"
:::

`SearchMemoryResponse` and `MemoryEntry` are ADK's types, and Memory Bank returns the same objects. One has a managed service behind it. Ours has a file.

Choose a file for one reason: you can open it and read it. Your agent's entire long-term memory is a page of text.

## So where do you point it?

To recap in this workshop implemention, two of the three services are chosen on the command line. The third we did our own implementation for the reason above:

| Service | Where you set it | This workshop |
|---|---|---|
| session | `--session_service_uri` on `adk web` | `sqlite+aiosqlite:///$WORKSHOP/sessions.db` |
| artifact | `--artifact_service_uri` on `adk web` | `file://$WORKSHOP/artifacts` |
| **memory** | **nowhere on the command line** | `MEMORY_DIR`, read inside `agent/concert/memory.py` |

So `memory.py` constructs the service itself, from an env var:

:::code path="agent/concert/memory.py" highlight="^MEMORY_DIR =|^MEMORY_USER =|^memory_service ="
:::

Get `MEMORY_DIR` sets where the agent reads it's memeory from and `MEMORY_USER` determines the file.

:::warn
**`MEMORY_USER` is not the session's user id, and that is deliberate.** `adk web` hardcodes `userId=user` and cannot be told otherwise, while your own server and the deployed service use something else. Key the file off the session and the memory file changes name depending on which surface you are on: your laptop writes `user.md` and Cloud Run reads something different. One fixed name is what lets a single memory file work across all three.
:::

:::warn
**We call this service from a tool, which is not where it belongs.** A memory service belongs on the Runner, and ADK then uses it for you:

```python
Runner(agent=root_agent, app_name="concert",
       session_service=...,
       memory_service=MarkdownMemoryService("./memory"))
```

That is what `monstertix/server.py` does. But `adk web` builds its services at startup from a URI, before it loads any of your code, so it cannot be handed an object. For the rest of this workshop the `recall` and `remember` tools call the service directly.
:::

## Go and find where things are

You now have four places that can hold a fact. Look at all four.

:::exercise id="run"
:::

## First, your own session

Three things went into storage, in three different places:

| | What was stored | Which tool did it | Where it went |
|---|---|---|---|
| 1 | Sam can't do weeknights | `note_companion` | `user:prefs`, in session state |
| 2 | the full seat map, 6 KB | `get_seatmap`, via `save_artifact` | the artifact service |
| 3 | a one-line seat map summary | `get_seatmap`, into `temp:seatmap` | **nowhere** |

In the **State** tab, notice that `temp:seatmap` is omitted. State keys with a `temp:` prefix exist only during the active invocation and are automatically stripped by ADK before persisting session state to the database.

## Then the older conversation

This session contains pre-populated conversation history in the database.

In the **event stream** (the middle column), notice that older turns have been replaced by a summarized event block.

In the **State** tab, three kinds of key are sitting there together:

```
target_event_id   ms-ams-01                      ← plain: this booking only
party_size        2                              ← plain: this booking only
user:prefs        {"excluded_weekdays": [...]}   ← the person, every session
```

The `user:` prefix (e.g. `user:prefs`) scopes state across all sessions for a given user. In contrast, **unprefixed keys (`target_event_id`, `party_size`)** represent plain session state, which is scoped strictly to the active session and is deleted when the session ends.

**Now compare the two State tabs.** While `user:prefs` and stored artifacts persist, `temp:seatmap` is absent from both sessions. State keys with a `temp:` prefix are strictly ephemeral and are never persisted to the database.

## Then the file

Three bookings, going back to January. The agent reads it when it calls `recall()`, and it will still be there even if we lost the session data.

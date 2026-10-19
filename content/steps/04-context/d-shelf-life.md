## The four places

| Where it lives | Survives the next message? | Survives a restart? | Survives deleting the session? |
|---|---|---|---|
| `temp:seatmap` | **no** | no | no |
| `party_size` — plain session state, in `two-days-ago` | yes | yes | no |
| `user:prefs` | yes | yes | **yes** |
| `memory/userx.md` | yes | yes | yes, and survives deleting the database |
| an artifact | yes | yes | depends on the service |

**Read that table as being about the containers, not about what is in them.**
`memory/userx.md` survives everything, and it only ever contains what `remember()`chose to put there. Nothing writes your current conversation into it. So the file outliving a session is not the same as the agent remembering what you were just talking about, and step 5 is where that distinction bites.

:::figure src="/docs-img/04-02-fivestage.png" caption="Five places a fact can live, and how long each lasts"
:::

## What state is

Think of state as a dictionary that travels with the session. Read and write it from your tools through `tool_context.state`, and let ADK save it alongside the conversation.

**ADK assigns the meaning of the prefixes.** You do not define them anywhere. ADK reads the first part of the key name and uses it to decide where the value goes and how long it lasts:

| A key called | ADK stores it | Lasts |
|---|---|---|
| `party_size` | with the session | until the session is deleted |
| `user:prefs` | against the user | across every session that user has |
| `app:tour_id` | against the app | across every user |
| `temp:seatmap` | nowhere | one invocation |

An **invocation** is a single request-response cycle, including all model reasoning, tool execution, and the final response.

When an invocation ends, ADK writes the new state to the database and strips every `temp:` key on the way.

:::note
**You will meet this again in two steps.** ADK's own `ResumabilityConfig` docstring says: *"Any temporary / in-memory state will be lost upon resumption."* Your agent is about to join a queue, stop running for forty minutes, and get woken up. `temp:` will not survive that.
:::

## One thing left unexplained

In `two-days-ago` you saw a summary sitting where somebody's first few turns used to be. Nothing you did put it there. ADK wrote it automatically once the conversation got long enough. Take that into the next step, which is about exactly this.

:::key
Every fact has a shelf life
:::

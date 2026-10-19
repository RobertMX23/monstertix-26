Leaving a process running polling continuously wastes memory, burns money, and crashes if your laptop sleeps or restarts.

:::exercise id="code"
:::

| File | What it is |
|---|---|
| `monstertix/server.py` | new. A web server with a Runner behind it |
| `monstertix/clock.py` | new. Something that knows the time and calls the server |

It has two halves, and they stay in two files all the way to the cloud:

:::figure src="/docs-img/03-02-ed.png" caption="The trigger and the triggerer, kept apart"
:::

| | | becomes, in step 9 |
|---|---|---|
| **the trigger** | an endpoint that can run the agent | Cloud Run |
| **the triggerer** | something with a clock, that calls it | Cloud Scheduler |

## The trigger — your own web server

Yes, a web server. Something has to be *listening* before anything can call it. The **ADK web UI** from the previous steps is a development interface that happens to be able to run an agent.

:::code path="monstertix/server.py" highlight="^runner = Runner\(|^@app\.post\(\x22/wake\x22\)|session_id or f\x22wake-|runner\.run_async\("
:::

An `Agent` does not run itself. It is a description: a name, a model, an instruction, a list of tools. Something has to take an incoming message, find the right session, hand the model the conversation so far, execute whichever tools it asks for, feed the results back, loop until it stops calling tools, and write every step of that to storage. That something is the `Runner`.

:::figure src="/docs-img/03-01-flow.png" caption="What a Runner does around your agent"
:::

The **ADK web UI** has a default one for you. Here you build it yourself, and that is the entire difference between the **ADK web UI** and something you can deploy.

:::file path="monstertix/server.py" label="Show server.py"
:::

## And a front door, while we are here

Despite `adk web` is a great development tool, it should not be something you ship. You should not enable it when deploying to production, and you would not point a customer at it if it did.
So the same server also serves a page.

**Meet MonsterTix.** A chat window, a name in the corner, two buttons. It posts to `/wake` and renders what comes back, and it would work unchanged against any endpoint that answers the same way.

| On the page | What it is underneath |
|---|---|
| the conversation | `POST /wake`, one message at a time |
| **+ New session** | a fresh session id — new conversation, and later, a new budget |
| **Reset memory** | deletes every session and the memory file. It asks first, and shows you exactly where that state lives |

:::exercise id="start"
:::

```
[server] agent concert · gemini-x-flash
[server] listening on http://xxxx_URL/wake
[server] nothing will happen until something calls it. Ctrl-C to stop.
```

Read that last line. The trigger is running and the agent is loaded, and nothing is happening. Separate the two ideas: being callable and being called.

:::note
From here to step 9 you will mostly use `adk web`, because seeing inside a run is what you are here to learn. But in step 9 the agent moves to Cloud Run and `adk web` stays within your developer laptop. This page is what deploys next to the agent as one service.
:::

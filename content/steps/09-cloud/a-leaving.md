On your laptop, an agent depends on your computer staying awake, local SQLite databases, and local files. If you close your laptop lid or deploy to a cloud container that restarts, local files and memory disappear.

To run reliably in production:

1. **Cloud Compute**: Run the agent in a container (like Cloud Run) that stays online.
2. **Durable Cloud Databases**: Replace local files and SQLite with cloud services (Cloud SQL for session data, Cloud Storage for files).
3. **Cloud Timers**: Use managed schedulers (like Cloud Scheduler and Pub/Sub) so the agent wakes up even when your laptop is turned off.

| File | What changed |
|---|---|
| `main.py` | new. One FastAPI serving the chat page **and** the endpoint a scheduler calls |
| `Dockerfile` | new. Ordinary python-slim and uvicorn. Nothing about it is ADK-specific |
| `requirements.txt` | new. Adds `asyncpg` for Postgres and `google-cloud-storage` for the bucket |
| `monstertix/` | copied in, so the page ships in the same container as the agent |
| `concert/` | **unchanged.** Byte-for-byte the folder you finished step 8 with |

:::exercise id="code"
:::

:::note
**Nothing about the agent changes to deploy it.** Copy `concert/` from step 8 into step 9 and diff it: the files are identical. Everything in this step is a new entrypoint, a container, and configuration. That is the result worth having — an agent that needed rewriting to be deployed would mean the earlier steps taught you the wrong shape.
:::

## The page you already built

Go back to the chat page from step 3. It has been sitting there since, waiting
for this step.

The **ADK web UI** is a developer tool. The State tab, the event stream and the graph are
what you want while you are learning, and none of it is something you hand to
another person. It does not exist on Cloud Run either.

The page does exactly what `adk web` did for you: talks to the agent, shows what
it said, lets you answer when it asks something. What it does not do is expose
your development tools to whoever has the URL.

:::app tab="monstertix"
:::

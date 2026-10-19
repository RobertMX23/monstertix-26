```
sessions.db          a SQLite file next to the code
memory/userx.md      a markdown file you can open in an editor
artifacts/           seat maps written to a folder
```

:::file path="memory/userx.md" label="Show memory/userx.md"
:::

**Keep all three for learning.** Open them, read them, edit the memory file and
watch the next answer change. Do not wish them into a database; nothing about a
workshop would be better for it.

Now expect all three to stop working the moment you deploy, and understand
exactly why rather than taking it on faith.

A Cloud Run container has a writable filesystem, so nothing errors when the agent
writes to it. But that filesystem belongs to **one instance**, and Cloud Run
starts and stops instances as traffic comes and goes. When yours stops, the disk
goes with it. Two more instances may be running beside it, each with its own copy
of a file it thinks is the only one.

So picture an agent joining a queue at 3am, writing the ticket to `sessions.db`,
and finding the file empty when something wakes it, or finding a different file
on a different instance. Look for an error or a crash and find neither. Just an
agent that has forgotten.

**What you need instead is state that outlives any one container.** Three
services, one for each file:

| On your laptop | In the cloud | What it is |
|---|---|---|
| `sessions.db` | **Cloud SQL** | a managed Postgres database. It exists whether or not anything is running |
| `memory/userx.md` | **Cloud Storage** | a bucket. Files as objects, reachable from every instance at once |
| `artifacts/` | **Cloud Storage** | the same bucket |
| `clock.py` | **Cloud Scheduler** | a cron that Google runs. Your terminal is not an alarm clock |

If those are new to you, read Cloud SQL as a database you do not run yourself,
Cloud Storage as a folder that lives on the internet, and Cloud Scheduler as a
cron job with retries and a timezone that keeps working when your laptop is shut.

## Create them

:::exercise id="state"
:::

```
→ instance  RUNNABLE
→ database  adk created
→ user      adk created
→ bucket    created
→ memory    memory/userx.md → gs://your-project-agent-you/memory/
✓ durable state ready. Written to .env
```

:::note
**Or ask for it instead.** If you have the **Google Cloud MCP server** connected to your coding assistant, you can describe what you want rather than run a script. Something like:

*"In project `<my-project>`, region `us-central1`: create a Cloud SQL Postgres instance called `workshop-sessions` on `db-f1-micro`, a database `adk` and a user `adk` on it, and a Cloud Storage bucket named after the project with uniform access. Then give me the connection name and a `postgresql+asyncpg://` URI that uses the Cloud Run unix socket."*

Read what it proposes before you approve it. The script exists so the workshop is reproducible; the prompt exists because this is how you will actually do it at work.
:::

That script created four things, one per row of the table above, and wrote two
URIs into `.env`:

```
CLOUD_SESSION_SERVICE_URI=postgresql+asyncpg://adk:…@/adk?host=/cloudsql/proj:region:instance
CLOUD_ARTIFACT_SERVICE_URI=gs://your-project-agent-you/artifacts
```

**Look at what those replaced.** `sqlite+aiosqlite:///…/sessions.db` became a
Postgres URI, and `file://…/artifacts` became `gs://…`. Recognise the same two
flags you have typed after `adk web` since step 4, and note that only the scheme
changed.

:::note
**`postgresql+asyncpg://`, not `postgresql://`.** ADK drives SQLAlchemy through its asyncio extension, so the driver has to be an async one and `asyncpg` has to be installed. Same trap as `aiosqlite` in step 6, and it fails the same way: fine until the first session write, which in the cloud is at 3am with nobody watching. The `host=/cloudsql/…` is a unix socket Cloud Run mounts for you, which is why the host looks like a path.
:::

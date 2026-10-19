With the services ready, give the agent its permanent home.

:::exercise id="deploy"
:::

That builds `agent/` into a container, pushes it to Cloud Run, and then wires up
three more things. Know what each is for, because "deploy the agent" is only the
first of five steps:

```
1. gcloud run deploy       the container: your agent, the graph, and the page
2. a Pub/Sub topic         a queue for messages
3. a service account       an identity, so the message is allowed in
4. a push subscription     topic ──► /trigger/wake
5. a Cloud Scheduler job   the alarm clock, on a cron
```

:::warn
**Why use `/trigger/wake` instead of ADK's built-in `/apps/<app>/trigger/pubsub`?**
ADK's default trigger creates a brand-new `session_id` and `user_id` for every incoming message:

```python
session_id = str(uuid.uuid4())
user_id    = subscription.replace("/", "--")
```

This works for stateless, one-off tasks. But for long-running workflows, a new session lacks existing context (queue tickets, budget, history) and would trigger a duplicate purchase instead of resuming the pending run.

`/trigger/wake` finds the user's existing parked session and resumes it.
:::

**Why a scheduler.** Go back to `clock.py` in step 3: sleep, then POST. It
worked, and it dies with your terminal. Cloud Scheduler is the same idea run by
Google: it fires on a cron, retries if the call fails, understands timezones, and
does not care whether your laptop is open. It is the trigger you already built,
living somewhere permanent.

**Why Pub/Sub in the middle.** Cloud Scheduler could call your service directly,
so the topic looks like an extra step. It buys you three things:

:::figure src="/docs-img/10-02-flow.png" caption="Scheduler publishes, Pub/Sub pushes, the agent wakes"
:::

**It holds the message.** Let the agent be deploying, restarting, or briefly
broken at 3am, and expect the message to wait instead of vanish. **It retries**,
so write no retry logic. And **it fans out**: subscribe a second thing that cares
about presales to the same topic tomorrow, without touching the scheduler.

That is why ADK gives you a trigger endpoint rather than expecting you to write
one. `trigger_sources=["pubsub"]` mounts a route that speaks Pub/Sub's push
format, so the message arrives as an invocation.

```
→ agent    https://concert-you-xxxx.run.app
→ topic    presale-you created
→ iam      concert-trigger@your-project… may invoke concert-you
→ push     → https://concert-you-xxxx.run.app/trigger/wake
→ schedule 0 3 * * *
```

:::note
**Asking for this instead.** With the Google Cloud MCP server connected, the five steps above are one request:

*"Deploy the folder `agent/` to Cloud Run in project `<my-project>` as `concert-me`, unauthenticated, with these environment variables: … Then create a Pub/Sub topic `presale-me`, a service account that may invoke the service, a push subscription from the topic to `<service-url>/trigger/wake`, and a Cloud Scheduler job firing the topic at 03:00 UTC daily."*

Read the plan before approving. The point of naming all five resources is that you can tell when one is missing.
:::

:::warn
**Trigger endpoints need Cloud Run or GKE.** Agent Runtime does not support scheduled or event-driven triggers, so this is not a choice between deployment targets.
:::

## Talk to it

Not the venue panel, not the **ADK web UI** — the service
you just deployed. This is MonsterTix, on the internet, with nothing of your
laptop involved.

It knows nothing about you. The memory file went into the bucket, but this is a
fresh session with no conversation in it.

:::exercise id="talk"
:::

Nobody typed. Scheduler published, Pub/Sub delivered, your endpoint found the
session that was waiting, and the run finished.

Here's how you can make it run every 5 mins:

```bash
gcloud scheduler jobs update pubsub presale-$(gcloud config get-value account | cut -d@ -f1) \
  --location=$GOOGLE_CLOUD_REGION --schedule="*/5 * * * *"
```

## Check the state is really durable

:::exercise id="durable"
:::

Your 3am run, as rows in a database that is not on your laptop. `gcloud sql
connect` is interactive, so run it in a terminal:

```bash
gcloud sql connect workshop-sessions --user=adk --database=adk
# password: 1234qwer  — fixed, and printed by setup-cloud-state.sh
```

```sql
select id, app_name, user_id from sessions;
select count(*) from events;
```

:::warn
**The interrupt that makes step 8 work will hang this one.** `agree_budget` stops the run and asks what you will spend. In front of a browser that is right. At 3am it is fatal: Pub/Sub delivers a message, the graph stops on a question, and nobody types an answer — so nothing is bought and nothing looks broken. That is what `someone_is_there()` is for: this run has no person behind it, so `agree_budget` takes the standing budget instead of stopping. **Anything that can stop and ask a person needs a way to know whether a person is there — per request, not per process.** The queue pause is different and fine — the next scheduled fire answers that one. A clock can answer a clock; only a person can answer a question.
:::

:::note
**Why Pub/Sub caps at ten minutes.** A push subscription gives your endpoint a limited window to acknowledge. That is exactly why `join_queue` returns immediately instead of blocking for forty minutes, and why `check_front` parks rather than waits. The work has to outlive the request that started it.
:::

:::key
The agent, its tools, its callbacks and the budget did not change. Two URIs
and one environment variable did.
:::

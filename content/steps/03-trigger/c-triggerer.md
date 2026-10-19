:::section
The trigger is listening now, but nothing calls it. The triggerer is the other half: something that knows the time and knocks on `/wake` when it is due. It has never heard of an agent, a Runner or a session. It knows a URL and a clock.

It is a very simple mechanism: sleep, POST, maybe repeat. Every scheduler you have used does the same, plus retries, timezones, and a guarantee that it survives a restart.

:::code path="monstertix/clock.py" highlight="time\.sleep\(args\.|client\.post\(f\x22\{TRIGGER_URL\}/wake\x22|if not args\.every"
:::
:::

:::note
**Local Scheduler Stand-in.** `clock.py` is a temporary local script. In production (Step 9), Cloud Scheduler replaces this script to provide managed, persistent execution triggers with automated retries.
:::

:::exercise id="fire"
:::

```
[clock] target   http://127.0.0.1:8090/wake
[clock] first fire in 60s, once only
[clock] go and watch the other terminal — do not touch the keyboard
```

A minute later, with nobody at the keyboard:

```
[clock]  firing → POST /wake
[server] woken · session wake-23930983
[server]   called search_events
[server]   called purchase
[server]   said   I've purchased 2 tickets for The Midnight Signal in
                  Amsterdam on Saturday, section A. Your total is 420.
[clock]  done. the agent ran and you were not involved.
```

That is the answer to step 2. Something outside the agent called it, and that something was a `sleep` and an HTTP request.

## Now read what it said

*"I've bought two tickets for The Midnight Signal in Amsterdam, section A, $420."*

Check the **venue panel** and you should see the ticket's been bought.

:::warn
**More than one order on the panel?** That is expected, and it is worth noticing rather than tidying away. Every fire of `clock.py` is a fresh wake with no memory of the last one, so if you ran it a few times, the agent bought a few times. Nothing stopped it, because nothing knew it had already happened.
:::

## So what is still wrong

It bought *something*. Look at what it had to guess. It picked Amsterdam and section A because they were the first thing it found, and you told the agent to buy it directly and it has no idea that Sam cannot do weeknights. **An agent that acts on guesses at 3am is worse than one that does nothing**.

:::note
**This is not an alarm clock yet.** The workbench started both halves, and they stop when it does. They are stand-ins. In step 9 `clock.py` is **deleted** and Cloud Scheduler does its job, and `server.py` becomes `main.py` — the same routes on top of `get_fast_api_app(trigger_sources=["pubsub"])`, in one Cloud Run container with the page. Nothing on the agent side changes, which is exactly why the two halves are separate files.
:::

:::note
**You now know three surfaces.** `adk web` for the rest of the workshop, because the State tab and the event stream are worth having while you learn. A bare `Runner` behind your own endpoint, for when nobody is watching. And in step 9, the same Runner behind ADK's Pub/Sub trigger endpoint. All three run the identical agent.
:::

:::key
Waking up is the easy half. An agent that wakes with nothing — no history, no preferences, nobody listening — is not yet worth waking.
:::

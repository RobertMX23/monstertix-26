Let's start this one with a conversation:

:::code path="agent/concert/nightly.py" highlight="^nightly = Workflow\(|edges=\[\(START, agree_budget"
:::

:::figure src="/docs-img/09-02-workflow.png" caption="The same graph, with agree_budget in front"
:::

It is step 7's graph with one node in front. Nothing else moved.

**Two nodes stop and wait, and they are the same mechanism.** `check_front` waits for a venue and is answered by a clock. `agree_budget` waits for a person and can only be answered by a person. That difference is the whole of step 9.

:::exercise id="run"
:::

In step 7 the graph had no user, so whatever you typed was thrown away and `go` did as well as anything. Here `agree_budget` calls `what_they_asked_for(ctx)` on its very first line, which collects everything you have typed and puts it in `state["request"]`. Then `open_the_night` hands it to the picker alongside the budget.

You did not name a day, and Amsterdam has two shows. So watch the picker fall
back to `recall()` for that, find *"Sam bails on weeknights"*, and take the
Saturday.

And in the browser, the run **stops** on an `adk_request_input` event:

**A graph just asked you a question.** Same interrupt as the queue wait in step 7, but it now pointed at a person to answer the question.

:::warn
**Answer in the box on the event, not the chat box.** The chat box starts a new invocation, which runs the graph from the top and asks you the same question again. Everything below depends on getting this right.
:::

Watch it stop and confirming:

```
[agree_budget] reading back: About a hundred for the cheap seats. Two-fifty
               if they're the good ones.

⚡ adk_request_input
   So: About a hundred for the cheap seats. Two-fifty if they're the good
   ones. Have I got that right?
```

```
[agree_budget] agreed: About a hundred for the cheap seats. Two-fifty if
               they're the good ones.
[open]         Budget: About a hundred for the cheap seats. Two-fifty if
               they're the good ones.
[pick_show]    → {"section": "A", "reason": "..."}
[queue_up]     ms-ams-01 section A — ticket q_5924edc2 at #14,203
[check_front]  #14,203 — not yet. Pausing.
```

**No prefix.** That is session state, and it is a decision worth making on purpose if you start a **New Session** and the budget will be gone, so it will asks you again.

:::note
**The cost of that choice.** An unattended run gets a fresh session, so it has no budget agreed and falls back to the default in `nightly.py`. That is a limit that has to be re-agreed each time, against a limit that outlives the conversation it came from.
:::

:::warn
**Watch whether it respects the memory file too.** `memory/userx.md` says this person could not see a thing from the upper bowl at Ziggo Dome — so section B is a defensible price and a bad seat. Sometimes it takes B anyway. That is not a bug in the budget; it is the honest cost of leaving a decision to a model, and it is the most useful thing on the screen if it happens. Ask it why it chose that section.
:::

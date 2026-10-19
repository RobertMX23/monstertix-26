:::exercise id="run"
:::

:::warn
**Nothing to show?** Compaction fires after three turns. If the script says nothing has been compacted yet, keep talking for another few turns and run it again.
:::

## Read what it wrote

Here is a real one, abridged:

```
── summary 1 ──────────────────────────────────────────────────────

Conversation Language: English

  **User Request:**
  The user initially wanted to know what concerts are playing in Amsterdam.
  Subsequently, the user provided a constraint regarding a companion, Sam.

  **Context Summary:**
  The user is planning a concert trip. The agent identified two events in
  Amsterdam: "The Midnight Signal" at the Ziggo Dome on Tuesday, November
  10 and Saturday, November 14, 2026. The user then informed the agent that a
  companion named "Sam" will be joining, but "he can't do weeknights." The
  agent has successfully noted this constraint for Sam.

  **Key Decisions/Information Obtained:**
  *   **City of interest:** Amsterdam
  *   **Events found:** "The Midnight Signal" at the Ziggo Dome, Tuesday
  10 November and Saturday 14 November 2026.
  *   **Companion:** Sam
  *   **Companion constraint:** Sam cannot attend concerts on weeknights.

  **Unresolved Questions/Tasks:**
  *   The agent has not explicitly confirmed if the found event (which is
  on a Saturday) is suitable given Sam's constraint, nor has it asked the
  user for the next steps regarding this event or further event searches.

  **Tools Used:**
  *   `recall`
  *   `search_events`
  *   `note_companion`
```

It kept the prices, the sections, the cities and the preferences, and correctly noted that nothing had been decided yet.

So look at what actually changed. Stop thinking of your conversation as what the model reads. **It gets this instead**: a description of your conversation, written by another model call, which you did not write and were never shown.

Three things follow from that:

**It is a paraphrase.** Nothing here is what anybody said. It is an account of what was said, produced by the same kind of process that produces everything else the model gets wrong occasionally.

:::note
Summary strings are stored in internal session event records and are not directly exposed as separate UI tabs.
:::

**It will happen again.** Every three turns, on a conversation that is now partly made of previous summaries.

## Try to book without repeating yourself

:::exercise id="book"
:::

Watch the agent ask which show, which section, and how many people. Mark that **correct**: the summary itself says the user never confirmed anything, so the agent asked. Give compaction the credit.

Even when compaction succeeds, summarizing previous turns can introduce ambiguity that requires the agent to re-confirm constraints with the user.

It reads the order back before it spends anything:

> *"You want to book 8 tickets in Section C for The Midnight Signal in Amsterdam
> on Saturday, November 14th. The total cost will be $760. Shall I go ahead and
> purchase these tickets?"*

Now it tells you it worked:

> *"Your purchase of 8 tickets in Section C for The Midnight Signal in Amsterdam
> on Saturday, November 14th, totaling $760, is complete. Your order ID is
> ord_227877fe."*

:::warn
**A new session would not pick up where this left off, and it is worth knowing exactly why.** Three different things are holding what you said, and only one of them travels. The **transcript and its summary** live in this session's events, so a new session starts blank. **Session state** like `budget_plan` is scoped to this session too, and goes with it. Only `user:prefs` and `memory/userx.md` cross the boundary. **Both survive, and neither helps**, which is not the contradiction it looks like: step 4's table was about which *stores* outlive a session, and this is about what is *in* them. Open `memory/userx.md` and you will find preferences and past bookings, because that is all `remember()` was ever called with. There is no line in it saying "we were discussing Amsterdam for four people", so a new session can read the whole file and still have no idea what "book us something" refers to.
:::

## Go and check whether it did

| On the panel | What you should see |
|---|---|
| **Tickets bought** | `1`, and *correct — one booking, one order* |
| the order underneath | `ord_xxxxxxxx — 8× section C · 760` |
| **The tour**, Amsterdam Saturday | section C is down by 8 |
| **Activity** | `ord_xxxxxxxx — 8x section C @ 95 = 760` |

Form this habit now, while the stakes are a mock ticket vendor. Check the panel to find out the ticket sale.

:::note
**A good summary is still a summary.** This step is often taught as "compaction loses things", and sometimes it does. The sharper problem is that it always *paraphrases*. Your agent's memory of the last twenty turns is now a piece of generated text nobody reviewed. It is usually fine. When it is not, there is no error, no log line, and nothing in the UI — the agent simply believes something slightly different from what you said.
:::

## Why `user:prefs` was the right choice

Recall `note_companion` writing Sam's constraint into `user:prefs` last step, and the obvious objection: why bother with a tool when the agent could just remember it.

Here is why. Keep state out of the conversation and no summary touches it. Check `user:prefs` and `budget_plan` against how they went in, and find them unchanged. Then check the transcript.

:::key
A summary keeps the general shape and loses the details. Store anything you
cannot afford to lose somewhere other than the conversation.
:::

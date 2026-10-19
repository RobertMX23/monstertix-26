# Writing the workbench's steps

Every page of the workbench comes from this folder. The server re-reads it on
each request, so an edit shows on reload; nothing needs rebuilding.

```
content/
  course.yaml                  title, credit
  steps/
    06-resumption/             NN-slug: NN is the order, slug is the URL
      step.yaml                meta, parts, exercises, checks
      a-the-wait.md            one part's reading
      b-pull-the-plug.md
  images/                      served at /content-images/
```

The codelab's own figures in `docs/img/` are served at `/docs-img/`, so a step
uses them without a copy: `:::figure src="/docs-img/06-02-intro.png"`.

## step.yaml

```yaml
title: Process resumption
kicker: Step 6
minutes: 15
color: amber            # cyan, purple, blue, amber, green, red, lime, teal
venue: true             # optional: the live venue panel in a left column (step 1)
stage: 6                # the solution step this page's code is
summary: One or two sentences under the title.
parts:
  - id: a
    label: The wait                     # the chip in the top bar
    headline: Waiting 40 minutes…       # the page title for this part
    body: a-the-wait.md
    exercises:                          # placed in the reading with :::exercise id="code"
      code:
        title: …
        intro: …
        tasks: [ … ]
    expect: [ … ]                       # "What you should see": top of the verify card
    checks: [ … ]                       # the Watch panel at the end of the part
    checksTitle: Watch                  # optional
```

### Tasks

**prepare** loads a step's code: stops the agent, presses RESET THE VENUE,
runs `./use-solution.sh N --force`, starts the agent again.

```yaml
- kind: prepare
  id: prepare
  step: 6
```

**files** is the file explorer. `stage`/`compare` mark files that step `stage`
adds (NEW) or changes (CHANGED) relative to step `compare`, with a bar beside
each changed line. `highlight` is a regular expression; matching lines are
tinted, and `highlightLabel` says in one sentence what they do. Mark the lines
that carry the idea, not every changed line.

```yaml
- kind: files
  id: files
  open: agent/concert/agent.py        # shown first
  stage: 6
  compare: 5
  only: [agent/concert/]              # default: agent/ and monstertix/
  highlight: 'LongRunningFunctionTool|ResumabilityConfig'
  highlightLabel: '`join_queue` is wrapped in …'
```

**turn** is the numbered list of things the student does. Each item has a
`text` (optional) and at most one action:

| Key | What the item shows |
|---|---|
| `say: "…"` + `in: agent` | a message to type, with a copy button that also brings that app forward |
| `answer: "…"` + `in: agent` | the same, for an `adk_request_input` event box (the page warns it is not the main chat box) |
| `press: SELL THE GOOD SEATS` + `venue: sellout` + `body: {…}` | a venue panel button: the same POST to `/admin/<venue>` |
| `service: agent` + `action: kill` | start, stop, restart or kill a service: `venue`, `agent`, `monstertix`, `clock` |
| `look: venue` | a button that brings `venue`, `agent` or `monstertix` forward |
| `run: ./show-compaction.sh` | runs a command from the repo root and shows its output |
| `clock: {in: 10, every: 0}` | starts `python -m monstertix.clock` with those arguments |
| only `text` | an instruction with no button |

The apps an exercise uses are framed right under its card, in tabs: every
`in:` and `look:` app, and the venue panel when there is a `press:`. To name
them yourself, give the exercise `apps: [agent, venue]`. Each app's card has
its process's switch, log, and (for the agent) kill -9 and Restart at its top
right. The venue starts with the workbench and is always on. The clock has no
app; a `clock:` item shows its switch and log beside the button.

Venue buttons (`venue:`): `reset`, `advance-queue` (SKIP THE WAIT), `sellout`
(body `{city, section}`), `hang-once` (BREAK THE NEXT PURCHASE), `clock`
(body `{multiplier}`).

### What you should see

`expect:` on a part is a short list of what the ADK web UI and the venue panel
should show once the student has done the "Your turn". It opens the verify card
at the end of the part, above the checks. Describe the screen in words (event
names, State keys, the panel's banner) rather than adding a screenshot after
the card.

```yaml
expect:
  - "After the restart: `⚡ check_queue` with the same `q_…` ticket, and a lower position."
```

### Checks

A check runs a read-only command and passes when it exits 0. The page shows
the command under "how", so it should be one a student could run.

```yaml
- id: saturday
  label: It queued for the Saturday show
  probe: python3 -m workbench.probe tool join_queue
  contains: ms-ams-01                 # optional: the output must also contain this
  hint: shown while the check has not passed
  expect: fail                        # optional: see below
  note: shown when an `expect: fail` row has happened
```

`expect: fail` marks a failure the step is built to show (step 2's agent that
never wakes). Write the probe so it passes when the
failure is observed; the row turns amber with an "expected" tag rather than
green.

Probes may only run `python3 -m workbench.probe …` or a reading `curl`.
`python -m workbench.probe --help` lists the questions it answers: `tool`,
`response`, `state`, `memory`, `artifacts`, `compaction`, `orders`, `queue`,
`killed`, `wake`, `session`, `pending`, `nodes`, `file`, `url`, `turns`.
`$VENUE_URL`, `$WORKSHOP`, `$PROJECT` and `$REGION` are filled in.

## The reading (.md)

Markdown, plus these blocks:

```
:::section kicker="Look on disk" headline="Where the ticket was"
…a card…
:::

:::key            the one sentence to remember
:::note           a developer's note
:::warn           a caution

:::figure src="/docs-img/06-02-intro.png" caption="…"
:::

:::file path="agent/concert/fence.py" label="Show fence.py"
:::

:::app tab="venue"         an app framed in the reading; tab="agent venue" for two
:::

:::exercise id="run"
Anything written in here is shown inside the "Your turn" card, under its
tasks: the walkthrough of the code its file explorer opens.
:::

:::code path="agent/concert/tools.py" highlight="^def note_companion"
:::

:::columns
one
---
two
:::
```

### Code

`:::code` shows a project file, never a pasted copy. A page has one file
explorer: the "Your turn" card's own if the page has one, otherwise the first
`:::code`. Every other `:::code` on the page is a button that opens its file
there and scrolls to it; `button="false"` only adds its lines to the
highlights. Explorers with a `stage` read that step's solution folder, so the
code is right before the student loads the step. `highlight` is a regular
expression; write a double quote inside it as `\x22`.

## Translations

English is the source. A translation sits next to it, one file at a time, and
anything not yet translated falls back to English:

```
06-resumption/
  step.yaml          English
  step.es.yaml       only the strings that differ in Spanish
  a-the-wait.md
  a-the-wait.es.md
course.es.yaml
```

A `step.<lang>.yaml` is merged over the English one: maps key by key, lists
of maps by `id` (by position for `turn` items, which have none). Leave out
`probe`, `run`, `venue`, `open`, `highlight` and other non-prose keys; the
English values are kept. A language appears in the page's language menu as
soon as one file exists for it.

The interface's own words are in `web/src/i18n/en.json`, rebuilt from the code
by `node web/scripts/i18n.mjs`. To translate them, copy it to `es.json`,
translate the values, and register it in `web/src/i18n/index.tsx`.

## Style

Write for the student at the keyboard: what to do, what they will see, why it
matters. End each sentence on the fact; no summarising clause after the point.

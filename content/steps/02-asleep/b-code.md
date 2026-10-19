You have seen it work and seen the trace. Now look at the code itself.

```
agent/concert/
├── agent.py     the agent — about twenty lines
├── tools.py     what it can do
├── venue.py     an httpx wrapper, nothing interesting
└── config.py    which model, and a credentials check
```

:::exercise id="code"
Open `agent/concert/agent.py`. The whole agent is the bottom of the file:

:::code path="agent/concert/agent.py" highlight="^INSTRUCTION = \x22\x22\x22|^root_agent = Agent\(|^    (name|model|instruction|tools)="
:::

A name, a model, some description of how agent should behave, and a list of Python functions. That is all an `Agent` is. `adk web` found it because the file is called `agent.py` and the variable is called `root_agent`.

Now `agent/concert/tools.py`:

:::code path="agent/concert/tools.py" highlight="^def search_events"
:::

An ordinary function. No decorator, no registration, no schema to write. ADK reads the signature and the docstring and builds the tool definition the model sees, which is why that docstring is load-bearing.

**The model never runs your code.** When you saw `search_events({"city": "Amsterdam"})`, the model was *asking* for that call. ADK ran the function, handed the result back, and the model wrote a sentence about it.
:::

# Agent Interface Example

`prepare_agent_case.py` loads the same Fire-Day from each role-specific CSV and emits a JSON case envelope. It uses only Python's standard library and does not contact an LLM provider.

From the repository root:

```bash
python agent_ready/examples/prepare_agent_case.py
```

To select a case:

```bash
python agent_ready/examples/prepare_agent_case.py \
  --incident-id 2016_4454556_TANNER \
  --fire-day-date 2017-01-01
```

The default output contains only the three decision-agent views. For scoring or post-hoc diagnosis, explicitly add `--include-critic`. Never use that option to construct a prediction-time prompt.

# Agent-Ready Interface

FireAgentBench treats an agent as an operational entity rather than as an LLM alone. For role (r), the released interface follows

```text
A_r = (M, V_r, I_r, S_r, P_r, C_r)
```

| Component | Meaning | Release artifact |
|---|---|---|
| `M` | Versioned LLM backbone and decoding settings selected by the experimenter | `configs/` |
| `V_r` | Role-specific observation boundary | Role-view CSV files, `agent_view_manifest.csv`, and `agent_role_registry.csv` |
| `I_r` | Role objective, constraints, and output instructions | `agent_prompt_templates.md` |
| `S_r` | Private context, message history, and optional frozen reflection memory | `schemas/agent_state.schema.json` |
| `P_r` | Observe--reason--message--revise execution policy | `protocols/agent_execution_protocol.md` |
| `C_r` | Typed inter-agent messages and permitted communication flow | `schemas/agent_message.schema.json` and `protocols/agent_execution_protocol.md` |

The dataset supplies the interface around `M`, but it does not redistribute model weights or fix one provider. Every reported experiment must freeze an exact model identifier or checkpoint, access date, inference settings, and model-specific reasoning mode.

## Roles and observation boundaries

The three decision agents receive mutually specialized projections of the same Fire-Day. The Geo Agent observes geographic and static landscape context; the Fire Behavior Agent observes incident dynamics, FIRMS activity, weather, and fuel moisture; and the Resource History Agent observes response history available through the current day. None of these views contains next-day labels.

The Critic Agent has two access modes. During prediction, it receives candidate conclusions and cited decision-time evidence only. During scoring or Task C diagnosis, it may additionally read `critic_agent_view.csv`, which contains ground truth and eligibility fields. Code must not load this file into a prediction-time context.

`agent_role_registry.csv` records the inputs, state scope, policy, message types, and ground-truth permissions for all four roles.

## Directory contents

```text
agent_ready/
├── README.md
├── agent_prompt_templates.md
├── agent_role_registry.csv
├── agent_view_manifest.csv
├── geo_agent_view.csv
├── fire_behavior_agent_view.csv
├── resource_history_agent_view.csv
├── critic_agent_view.csv
├── configs/
│   ├── model_config.schema.json
│   ├── single_agent.example.json
│   └── homogeneous_multi_agent.example.json
├── schemas/
│   ├── agent_definition.schema.json
│   ├── agent_message.schema.json
│   ├── agent_state.schema.json
│   └── task_c_output.schema.json
├── protocols/
│   ├── agent_execution_protocol.md
│   └── task_c_self_evolution_protocol.md
└── examples/
    ├── README.md
    └── prepare_agent_case.py
```

## Reproducibility requirements

1. Use identical views, prompt templates, output schemas, and split membership across compared models.
2. Give each role a separate context and state object, even when all roles use the same LLM.
3. Record every inter-agent message with its case key, sender, recipients, phase, and cited fields.
4. Keep prediction and post-hoc diagnosis contexts separate. Ground truth may enter only after the prediction has been committed.
5. Derive prompt, policy, or memory updates on train/development cases and freeze them before held-out evaluation.
6. Report both task performance and inference usage, including model calls, generated tokens, latency, and communication rounds.

## Minimal workflow

Generate a role-separated case envelope with only Python's standard library:

```bash
python agent_ready/examples/prepare_agent_case.py
```

Select a specific case with `--incident-id` and `--fire-day-date`. Add `--include-critic` only for scoring or post-hoc diagnosis. The script prepares inputs; it does not call an external model or write predictions.

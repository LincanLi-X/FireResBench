# FireAgentBench Agent Prompt Templates

This document defines the prompt templates for the four agent roles used in FireAgentBench. The benchmark dataset provides structured CSV views only. During experiments, each evaluated model should generate natural-language observations, reasoning, or predictions dynamically from the corresponding CSV view and prompt template.

The prompts instantiate the instruction component in the role-agent definition `A_r = (M, V_r, I_r, S_r, P_r, C_r)`. Model configuration, state, execution policy, and communication are specified separately in `configs/`, `schemas/`, and `protocols/`; changing a prompt alone does not define a new Agent architecture.

## General Rules

All agents must follow these rules:

```text
1. Use only the fields provided in the current agent view.
2. Do not invent missing fields, fire causes, weather conditions, resource needs, or future outcomes.
3. Do not mechanically list every field; instead, summarize the most important operational signals.
4. If a key field is missing, state that it is unavailable. Minor missing fields can be ignored.
5. Keep the output concise, factual, and suitable for wildfire management decision support.
6. Except for the Critic Agent, agents must not see or mention ground-truth labels.
7. Non-Critic agents must not use supervised label fields such as daily_personnel, daily_cost_usd, resource_action, eligible_*, or label_status.
```

Recommended observation length for each agent:

```text
2-3 sentences
60-90 English words
```

In experiments, each CSV row can be converted into JSON and inserted into the prompt, for example:

```text
Input row:
{agent_view_row_json}
```

## 1. Geo Agent

### Input View

```text
agent_ready/geo_agent_view.csv
```

### Role

The Geo Agent summarizes the geographic and static landscape context of the wildfire incident. It focuses on location, county and state context, jurisdictional information, terrain, fuel model indicators, and LANDFIRE EVT/EVC/EVH vegetation features.

### Prompt Template

```text
You are the Geo Agent in FireAgentBench, a wildfire management benchmark.

Your task is to summarize the geographic and static landscape context of the current Fire-Day case. Use only the fields provided in the Geo Agent input row.

Focus on:
- reported incident location, county, state, and coordinates;
- jurisdiction, protection unit, and location confidence if available;
- terrain and fuel model fields;
- LANDFIRE EVT/EVC/EVH dominant classes and top-1 proportions at 1 km and 5 km;
- whether the local landscape appears spatially concentrated, mixed, or uncertain based on LANDFIRE proportions.

Do not discuss personnel, cost, next-day labels, resource_action, or any future outcome.
Do not infer information that is not present in the input.

Write 2-3 concise sentences, 60-90 words total.

Input row:
{geo_agent_view_row_json}

Return only the Geo Agent observation.
```

### Expected Output

```text
A concise natural-language observation about location, terrain, jurisdiction, fuel and vegetation context, and spatial reliability.
```

## 2. Fire Behavior Agent

### Input View

```text
agent_ready/fire_behavior_agent_view.csv
```

### Role

The Fire Behavior Agent summarizes the current Fire-Day's fire activity and environmental context. It focuses on fire size, growth, containment, satellite fire detections, weather, and fuel-moisture conditions.

### Prompt Template

```text
You are the Fire Behavior Agent in FireAgentBench, a wildfire management benchmark.

Your task is to summarize the current and recent fire-behavior context of the current Fire-Day case. Use only the fields provided in the Fire Behavior Agent input row.

Focus on:
- current fire size, new acres, recent area trend, and containment;
- observed fire behavior flags, if available;
- FIRMS detections within 1 km and 5 km, including count and FRP;
- gridMET weather and fuel indicators, including Burning Index, wind speed, temperature, fm100, and fm1000;
- whether the available evidence suggests active spread, moderate activity, low activity, or uncertainty.

Do not discuss next-day daily_personnel, daily_cost_usd, resource_action, or label eligibility.
Do not infer future resource decisions.

Write 2-3 concise sentences, 60-90 words total.

Input row:
{fire_behavior_agent_view_row_json}

Return only the Fire Behavior Agent observation.
```

### Expected Output

```text
A concise natural-language observation about fire activity, satellite evidence, weather and fuel conditions, containment status, and growth signals.
```

## 3. Resource History Agent

### Input View

```text
agent_ready/resource_history_agent_view.csv
```

### Role

The Resource History Agent summarizes the operational response history known up to the current Fire-Day. It focuses on personnel, cost, recent resource trends, command structure, suppression context, evacuations, closures, structural exposure, and reported impacts.

### Prompt Template

```text
You are the Resource History Agent in FireAgentBench, a wildfire management benchmark.

Your task is to summarize the resource-use and operational history available up to the current Fire-Day. Use only the fields provided in the Resource History Agent input row.

Focus on:
- current personnel and aerial resources;
- recent personnel changes and rolling personnel trends;
- cost-to-date, average daily cost, and recent cost trends;
- suppression method, incident management organization, dispatch priority, and unified command if available;
- evacuations, road/trail/area closures, threatened or damaged structures, injuries, and fatalities as indicators of operational complexity.

Do not reveal or infer next-day ground-truth labels such as daily_personnel, daily_cost_usd, or resource_action.
Do not recommend a final resource action unless explicitly asked by the experiment protocol.

Write 2-3 concise sentences, 60-90 words total.

Input row:
{resource_history_agent_view_row_json}

Return only the Resource History Agent observation.
```

### Expected Output

```text
A concise natural-language observation about resource posture, cost pressure, recent trends, and operational complexity.
```

## 4. Critic Agent

### Input View

```text
agent_ready/critic_agent_view.csv
```

### Role

The Critic Agent reviews the complete Fire-Day case for evaluation, quality control, error analysis, and self-evolution failure diagnosis. Unlike the other agents, it may access all input fields and ground-truth labels when the experiment protocol permits evaluation or diagnosis.

### Prompt Template

```text
You are the Critic Agent in FireAgentBench, a wildfire management benchmark.

Your task is to summarize the complete Fire-Day case for evaluation and error analysis. You may use all fields provided in the Critic Agent input row, including ground-truth labels and eligibility fields.

Focus on:
- the main geographic evidence;
- the main fire-behavior and weather/fuel evidence;
- the main resource-history evidence;
- whether daily_personnel, daily_cost_usd, and resource_action labels are available and eligible;
- any reason the case should be used, excluded, or treated cautiously in supervised evaluation.

Do not invent a model prediction.
Do not claim that a model is correct or incorrect unless a prediction is explicitly provided by the experiment protocol.

Write 2-3 concise sentences, 60-90 words total.

Input row:
{critic_agent_view_row_json}

Return only the Critic Agent observation.
```

### Expected Output

```text
A concise natural-language case-level summary that supports evaluation, label checking, and failure analysis.
```

## Recommended Experiment Usage

For a multi-agent experiment:

```text
1. Select one Fire-Day case by incident_id + fire_day_date.
2. Load the corresponding row from each agent-specific CSV view.
3. Fill the row JSON into the corresponding prompt template.
4. Call the selected agent model to produce each agent's observation or reasoning.
5. Combine agent outputs according to the experiment protocol.
6. Compare final predictions against labels in the critic view or label files.
```

For fair comparison across different agent models:

```text
Use the same CSV views and the same prompt templates for all evaluated models.
Do not pre-generate observations with one model and then use them to evaluate another model.
Keep non-Critic agents isolated from label fields.
```

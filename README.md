# Financial Operations Observability & Integration Analytics Framework

**Open operational observability and integration analytics framework prototype for heterogeneous financial systems.**

## What this is

This project is a portfolio-quality Python framework prototype that demonstrates
how operational finance events from different systems can be ingested,
normalized, replayed, and analyzed through an observability-first architecture.

It is intentionally focused on operations analytics, not trading or prediction.

Core message:

**Different operational systems speak different dialects. This framework demonstrates how they can be normalized into a unified analytics and observability layer.**

## Why operational observability matters

Finance operations teams rely on many systems that rarely share one canonical
event model: loan servicing exports, CRM pipelines, underwriting engines,
payment processors, ESG feeds, investor reporting tools, and integration logs.

Without normalization and replay, teams struggle to answer practical questions:

- Where are workflow bottlenecks?
- Which integrations are creating latency and failures?
- Where are payment delays and escalations increasing risk?
- How do operational and ESG signals shift over time across regions and teams?

This prototype shows one way to answer those questions with a reusable,
modular analytics framework.

## Architecture

```text
financial-operations-observability-framework/
  app.py
  README.md
  requirements.txt
  sample_data/
    finance_ops_sample.csv
  finance_ops/
    __init__.py
    schema.py
    generator.py
    ingestion.py
    replay.py
    visualization.py
    utils.py
    analytics/
      __init__.py
      metrics.py
      anomalies.py
      workflows.py
      risk.py
      payments.py
      integrations.py
      esg.py
      reporting.py
  tests/
    test_schema.py
    test_metrics.py
    test_anomalies.py
    test_workflows.py
```

Framework flow:

1. Ingest heterogeneous event streams
2. Normalize to canonical schema
3. Reconstruct workflows and replay timelines
4. Compute modular operational analytics
5. Visualize observability outcomes in Streamlit

### Transformation flow diagram (ASCII)

```text
Heterogeneous Source Dialects
  - Loan servicing exports
  - CRM event logs
  - Payment processor events
  - Underwriting decisions
  - ESG updates
  - Investor/reporting snapshots
  - Integration incident logs
            |
            v
+-----------------------------+
| finance_ops/ingestion.py    |
| ingest_events(source, cfg)  |
| - detect input format       |
| - map common aliases        |
| - route sample vs CSV path  |
+-----------------------------+
            |
            v
+----------------------------------------+
| finance_ops/schema.py                  |
| normalize_event_dataframe(df)          |
| - parse timestamps                     |
| - coerce numeric fields                |
| - standardize enums/strings            |
| - fill optional defaults               |
| - clip ranges + boolean normalization  |
| - sort chronologically                 |
+----------------------------------------+
            |
            v
Canonical Operational Event Layer
  columns:
  timestamp, source_system, entity_type, entity_id, customer_id,
  workflow_stage, workflow_status, event_type, transaction_amount,
  payment_status, risk_score, esg_score, region, assigned_team,
  latency_ms, integration_status, anomaly_flag, notes
            |
    +-------+----------------------+---------------------+
    |                              |                     |
    v                              v                     v
Replay / State                 Analytics Modules      Visualization
finance_ops/replay.py          finance_ops/analytics  finance_ops/
- snapshots                    - metrics              visualization.py
- timeline reconstruction       - workflows            - pipeline, timeline
- operational day replay        - anomalies            - risk, payments
- workflow state                - risk                 - integrations
                                - payments             - anomalies
                                - integrations         - replay + bottlenecks
                                - esg
                                - reporting
            |
            v
Streamlit Application (app.py)
  Overview | Data Sources | Workflow Pipeline | Replay | Payments |
  Risk | ESG | Integration Health | Anomaly Detection | Latency |
  Bottlenecks | Entity Timeline | Framework About
```

## Normalized schema

Canonical event fields include:

- `timestamp`
- `source_system`
- `entity_type`
- `entity_id`
- `customer_id`
- `workflow_stage`
- `workflow_status`
- `event_type`
- `transaction_amount`
- `payment_status`
- `risk_score`
- `esg_score`
- `region`
- `assigned_team`
- `latency_ms`
- `integration_status`
- `anomaly_flag`
- `notes`

Schema helpers in `finance_ops/schema.py`:

- `get_required_columns()`
- `get_optional_columns()`
- `validate_event_dataframe(df)`
- `normalize_event_dataframe(df)`

## Ingestion layer

`finance_ops/ingestion.py` provides a unified entrypoint:

- `ingest_events(source, config=None)`
- `load_sample_data(config)`
- `load_csv(file)`
- `detect_input_format(file_name)`

Current support:

- generated sample data
- CSV uploads

Architecture is adapter-oriented and ready to extend toward:

- Salesforce/HubSpot-style CRM feeds
- loan servicing APIs
- payment processor webhooks
- ESG vendor datasets
- investor reporting systems
- platform integration logs

## Replay systems

`finance_ops/replay.py` includes operational replay primitives:

- `get_system_snapshot(df, timestamp)`
- `reconstruct_entity_timeline(df, entity_id)`
- `replay_operational_day(df, timestamp)`
- `calculate_workflow_state(df)`

These functions model event reconstruction, workflow state replay, and
audit-oriented investigation patterns.

## Analytics modules

The analytics layer is modular and reusable:

- `metrics.py`: KPI cards, stage/region/team summaries, latency summaries
- `workflows.py`: transition graphs, durations, bottlenecks
- `anomalies.py`: payment, latency, integration, stall, risk, and ESG anomalies
- `risk.py`: risk distributions, clusters, regional comparisons, trend tracking
- `payments.py`: payment timelines, delinquency, delays, collections escalations
- `integrations.py`: integration health, failures, latency, sync gaps
- `esg.py`: ESG distribution, regional analysis, temporal changes
- `reporting.py`: investor, export, and audit summaries

## Example operational workflows this prototype models

- Intake -> underwriting -> compliance review -> approval -> funding -> servicing
- Delayed payment -> collections escalation -> integration degradation
- Reporting snapshot generation across regions and investor feeds
- ESG update events with drift/inconsistency detection
- Integration incidents and recovery lifecycle

## Streamlit app sections

The demo app (`app.py`) includes:

- Overview
- Data Sources
- Workflow Pipeline
- Operational Replay
- Payment Analytics
- Risk Analytics
- ESG Metrics
- Integration Health
- Anomaly Detection
- Operational Latency
- Workflow Bottlenecks
- Entity Timeline Replay
- About This Framework

## How to run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m streamlit run app.py
```

Optional: run tests

```bash
python -m pytest
```

Optional: generate and save sample CSV

```bash
python -c "from finance_ops.generator import generate_sample_finance_operations_data as g; g().to_csv('sample_data/finance_ops_sample.csv', index=False)"
```

## Future roadmap

- webhook ingestion adapters
- Kafka/Kinesis integration
- OpenTelemetry integration
- cloud deployment patterns
- API layer for programmatic analytics access
- multi-user collaboration workflows
- audit export bundles and signed evidence trails
- AI-assisted operational summaries and incident narratives

## Simplifications in this prototype

- no production auth, tenancy, or RBAC
- no persistent database or message queue
- no heavy machine learning dependencies
- no cloud infra orchestration
- all data is simulated but designed to look operationally realistic

These choices keep the prototype lightweight while still demonstrating
architecture, observability thinking, and integration systems design.

"""Sample data generator for financial operations observability workflows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

from .schema import normalize_event_dataframe

WORKFLOW_STAGES = [
    "intake",
    "underwriting",
    "compliance_review",
    "approval",
    "funding",
    "servicing",
    "collections",
    "reporting",
]

REGIONS = ["North America", "Latin America", "Europe", "Africa", "Asia Pacific"]
TEAMS = ["Intake Ops", "Underwriting Ops", "Servicing Ops", "Collections Ops", "Compliance Ops"]


def _workflow_status_for_stage(stage: str, risk_score: float, rng: np.random.Generator) -> str:
    if stage == "collections":
        return "in_progress" if rng.random() < 0.65 else "completed"
    if risk_score > 80.0 and stage in {"underwriting", "compliance_review"} and rng.random() < 0.35:
        return "delayed"
    return "completed"


def _integration_status(risk_score: float, rng: np.random.Generator) -> str:
    failure_prob = 0.015 + max(0.0, (risk_score - 60.0)) * 0.0009
    degraded_prob = 0.05 + max(0.0, (risk_score - 50.0)) * 0.0012
    draw = rng.random()
    if draw < failure_prob:
        return "failed"
    if draw < failure_prob + degraded_prob:
        return "degraded"
    return "healthy"


def _base_latency_ms(stage: str, integration_status: str, rng: np.random.Generator) -> float:
    stage_baseline = {
        "intake": 140.0,
        "underwriting": 280.0,
        "compliance_review": 320.0,
        "approval": 220.0,
        "funding": 260.0,
        "servicing": 190.0,
        "collections": 240.0,
        "reporting": 210.0,
    }
    baseline = stage_baseline.get(stage, 220.0)
    noise = rng.lognormal(mean=np.log(max(10.0, baseline)), sigma=0.35)
    if integration_status == "degraded":
        noise *= rng.uniform(1.3, 2.0)
    elif integration_status == "failed":
        noise *= rng.uniform(2.1, 4.0)
    return float(noise)


def _append_event(records: list[dict[str, object]], **kwargs: object) -> None:
    records.append(
        {
            "timestamp": kwargs.get("timestamp"),
            "source_system": kwargs.get("source_system", "workflow_orchestrator"),
            "entity_type": kwargs.get("entity_type", "loan_case"),
            "entity_id": kwargs.get("entity_id", "unknown_entity"),
            "customer_id": kwargs.get("customer_id", "unknown_customer"),
            "workflow_stage": kwargs.get("workflow_stage", "intake"),
            "workflow_status": kwargs.get("workflow_status", "in_progress"),
            "event_type": kwargs.get("event_type", "event_logged"),
            "transaction_amount": kwargs.get("transaction_amount", 0.0),
            "payment_status": kwargs.get("payment_status", "not_applicable"),
            "risk_score": kwargs.get("risk_score", np.nan),
            "esg_score": kwargs.get("esg_score", np.nan),
            "region": kwargs.get("region", "unknown_region"),
            "assigned_team": kwargs.get("assigned_team", "unassigned"),
            "latency_ms": kwargs.get("latency_ms", np.nan),
            "integration_status": kwargs.get("integration_status", "unknown"),
            "anomaly_flag": kwargs.get("anomaly_flag", False),
            "notes": kwargs.get("notes", ""),
        }
    )


def generate_sample_finance_operations_data(
    num_customers: int = 500,
    num_loans: int = 1000,
    days: int = 90,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate realistic, heterogeneous finance operations event data."""
    if num_customers < 20:
        raise ValueError("num_customers must be >= 20")
    if num_loans < 50:
        raise ValueError("num_loans must be >= 50")
    if days < 14:
        raise ValueError("days must be >= 14")

    rng = np.random.default_rng(seed)
    now = datetime.now(tz=timezone.utc).replace(microsecond=0)
    start_time = now - timedelta(days=int(days))

    customer_ids = [f"CUS-{idx:05d}" for idx in range(1, num_customers + 1)]
    loan_ids = [f"LOAN-{idx:06d}" for idx in range(1, num_loans + 1)]

    customer_region = {customer_id: str(rng.choice(REGIONS)) for customer_id in customer_ids}
    customer_team = {customer_id: str(rng.choice(TEAMS)) for customer_id in customer_ids}

    base_risk = {
        customer_id: float(np.clip(rng.normal(52.0, 14.0), 8.0, 97.0))
        for customer_id in customer_ids
    }
    base_esg = {
        customer_id: float(np.clip(rng.normal(64.0, 12.0), 5.0, 99.0))
        for customer_id in customer_ids
    }

    records: list[dict[str, object]] = []

    for loan_id in loan_ids:
        customer_id = str(rng.choice(customer_ids))
        region = customer_region[customer_id]
        team = customer_team[customer_id]

        loan_amount = float(np.round(rng.lognormal(mean=np.log(240_000), sigma=0.55), 2))
        risk_score = float(np.clip(base_risk[customer_id] + rng.normal(0.0, 7.5), 0.0, 100.0))
        esg_score = float(np.clip(base_esg[customer_id] + rng.normal(0.0, 5.0), 0.0, 100.0))

        stage_start = start_time + timedelta(hours=float(rng.uniform(0.0, days * 24 * 0.4)))
        stage_time = stage_start

        for stage in WORKFLOW_STAGES:
            status = _workflow_status_for_stage(stage, risk_score, rng)
            integration_status = _integration_status(risk_score, rng)
            latency_ms = _base_latency_ms(stage, integration_status, rng)

            source_system = {
                "intake": "crm_platform",
                "underwriting": "underwriting_engine",
                "compliance_review": "loan_servicing_export",
                "approval": "workflow_orchestrator",
                "funding": "payment_processor",
                "servicing": "loan_servicing_export",
                "collections": "loan_servicing_export",
                "reporting": "investor_reporting_feed",
            }.get(stage, "workflow_orchestrator")

            event_type = f"{stage}_stage_entered"
            anomaly_flag = bool(integration_status == "failed" or latency_ms > 1500.0)

            _append_event(
                records,
                timestamp=stage_time,
                source_system=source_system,
                entity_type="loan_case",
                entity_id=loan_id,
                customer_id=customer_id,
                workflow_stage=stage,
                workflow_status=status,
                event_type=event_type,
                transaction_amount=loan_amount if stage in {"funding", "servicing"} else 0.0,
                payment_status="pending" if stage in {"funding", "servicing", "collections"} else "not_applicable",
                risk_score=risk_score,
                esg_score=esg_score,
                region=region,
                assigned_team=team,
                latency_ms=latency_ms,
                integration_status=integration_status,
                anomaly_flag=anomaly_flag,
                notes="workflow transition",
            )

            if stage == "underwriting" and (risk_score > 74.0 or rng.random() < 0.12):
                review_delay = timedelta(hours=float(rng.uniform(6.0, 28.0)))
                _append_event(
                    records,
                    timestamp=stage_time + review_delay,
                    source_system="underwriting_engine",
                    entity_type="underwriting_decision",
                    entity_id=f"UW-{loan_id}",
                    customer_id=customer_id,
                    workflow_stage="underwriting",
                    workflow_status="escalated" if risk_score > 80.0 else "in_progress",
                    event_type="manual_review_opened",
                    transaction_amount=0.0,
                    payment_status="not_applicable",
                    risk_score=min(100.0, risk_score + float(rng.uniform(1.0, 8.0))),
                    esg_score=esg_score,
                    region=region,
                    assigned_team="Compliance Ops",
                    latency_ms=_base_latency_ms("underwriting", "degraded", rng),
                    integration_status="degraded",
                    anomaly_flag=True,
                    notes="manual underwriting review",
                )

            stage_duration_hours = {
                "intake": rng.uniform(3.0, 16.0),
                "underwriting": rng.uniform(8.0, 48.0),
                "compliance_review": rng.uniform(6.0, 38.0),
                "approval": rng.uniform(4.0, 20.0),
                "funding": rng.uniform(4.0, 24.0),
                "servicing": rng.uniform(24.0, 320.0),
                "collections": rng.uniform(24.0, 180.0),
                "reporting": rng.uniform(8.0, 36.0),
            }[stage]

            if integration_status == "failed":
                stage_duration_hours *= float(rng.uniform(1.4, 2.8))
            if risk_score > 78.0 and stage in {"underwriting", "compliance_review", "collections"}:
                stage_duration_hours *= float(rng.uniform(1.2, 1.8))

            stage_time = stage_time + timedelta(hours=float(stage_duration_hours))

        payment_count = int(rng.integers(2, 8))
        payment_base_time = stage_start + timedelta(days=float(rng.uniform(12.0, max(18.0, days * 0.85))))
        payment_amount = float(np.round(loan_amount / max(2, payment_count), 2))

        for payment_idx in range(payment_count):
            payment_time = payment_base_time + timedelta(days=payment_idx * float(rng.uniform(14.0, 32.0)))
            delay_factor = max(0.0, risk_score - 55.0) / 100.0
            delayed_probability = 0.09 + delay_factor * 0.35
            failed_probability = 0.02 + delay_factor * 0.15

            draw = rng.random()
            if draw < failed_probability:
                payment_status = "failed"
            elif draw < failed_probability + delayed_probability:
                payment_status = "delayed"
            else:
                payment_status = "completed"

            integration_status = "healthy"
            if payment_status == "failed":
                integration_status = "failed"
            elif payment_status == "delayed" and rng.random() < 0.55:
                integration_status = "degraded"

            latency_ms = _base_latency_ms("servicing", integration_status, rng)
            anomaly_flag = bool(payment_status in {"delayed", "failed"} or latency_ms > 1200.0)

            _append_event(
                records,
                timestamp=payment_time,
                source_system="payment_processor",
                entity_type="payment",
                entity_id=f"PAY-{loan_id}-{payment_idx + 1}",
                customer_id=customer_id,
                workflow_stage="servicing" if payment_status == "completed" else "collections",
                workflow_status="completed" if payment_status == "completed" else "delayed",
                event_type="payment_processed" if payment_status == "completed" else "payment_exception",
                transaction_amount=payment_amount,
                payment_status=payment_status,
                risk_score=risk_score,
                esg_score=esg_score,
                region=region,
                assigned_team="Servicing Ops" if payment_status == "completed" else "Collections Ops",
                latency_ms=latency_ms,
                integration_status=integration_status,
                anomaly_flag=anomaly_flag,
                notes="scheduled payment cycle",
            )

            if payment_status in {"delayed", "failed"}:
                _append_event(
                    records,
                    timestamp=payment_time + timedelta(hours=float(rng.uniform(10.0, 50.0))),
                    source_system="loan_servicing_export",
                    entity_type="workflow_event",
                    entity_id=f"ESC-{loan_id}-{payment_idx + 1}",
                    customer_id=customer_id,
                    workflow_stage="collections",
                    workflow_status="escalated",
                    event_type="collections_escalation",
                    transaction_amount=0.0,
                    payment_status=payment_status,
                    risk_score=min(100.0, risk_score + float(rng.uniform(2.0, 10.0))),
                    esg_score=esg_score,
                    region=region,
                    assigned_team="Collections Ops",
                    latency_ms=_base_latency_ms("collections", "degraded", rng),
                    integration_status="degraded",
                    anomaly_flag=True,
                    notes="collections workflow escalation",
                )

    for customer_id in customer_ids:
        region = customer_region[customer_id]
        team = customer_team[customer_id]

        crm_event_count = int(rng.integers(2, 7))
        for _ in range(crm_event_count):
            event_time = start_time + timedelta(hours=float(rng.uniform(0.0, days * 24.0)))
            event_type = str(rng.choice(["customer_contacted", "document_requested", "case_note_added", "follow_up_scheduled"]))
            _append_event(
                records,
                timestamp=event_time,
                source_system="crm_platform",
                entity_type="customer_profile",
                entity_id=f"CRM-{customer_id}",
                customer_id=customer_id,
                workflow_stage=str(rng.choice(["intake", "servicing", "collections"])),
                workflow_status="in_progress",
                event_type=event_type,
                transaction_amount=0.0,
                payment_status="not_applicable",
                risk_score=float(np.clip(base_risk[customer_id] + rng.normal(0.0, 2.0), 0.0, 100.0)),
                esg_score=float(np.clip(base_esg[customer_id] + rng.normal(0.0, 2.0), 0.0, 100.0)),
                region=region,
                assigned_team=team,
                latency_ms=_base_latency_ms("intake", "healthy", rng),
                integration_status="healthy",
                anomaly_flag=False,
                notes="crm interaction",
            )

        esg_updates = max(2, days // 30)
        for update_idx in range(esg_updates):
            update_time = start_time + timedelta(days=(update_idx + 1) * (days / (esg_updates + 1)))
            drift = float(rng.normal(0.0, 4.0))
            updated_esg = float(np.clip(base_esg[customer_id] + drift, 0.0, 100.0))
            anomaly_flag = bool(abs(drift) > 10.5)
            _append_event(
                records,
                timestamp=update_time,
                source_system="esg_impact_feed",
                entity_type="esg_profile",
                entity_id=f"ESG-{customer_id}",
                customer_id=customer_id,
                workflow_stage="reporting",
                workflow_status="completed",
                event_type="esg_score_updated",
                transaction_amount=0.0,
                payment_status="not_applicable",
                risk_score=base_risk[customer_id],
                esg_score=updated_esg,
                region=region,
                assigned_team="Compliance Ops",
                latency_ms=_base_latency_ms("reporting", "healthy", rng),
                integration_status="healthy",
                anomaly_flag=anomaly_flag,
                notes="esg profile refresh",
            )

    report_dates = pd.date_range(start_time.date(), now.date(), freq="7D")
    for report_time in report_dates:
        for region in REGIONS:
            _append_event(
                records,
                timestamp=pd.Timestamp(report_time).to_pydatetime().replace(tzinfo=timezone.utc),
                source_system="investor_reporting_feed",
                entity_type="report_batch",
                entity_id=f"RPT-{region[:2].upper()}-{pd.Timestamp(report_time).strftime('%Y%m%d')}",
                customer_id="investor_pool",
                workflow_stage="reporting",
                workflow_status="completed",
                event_type="investor_report_generated",
                transaction_amount=float(rng.uniform(2_000_000, 40_000_000)),
                payment_status="not_applicable",
                risk_score=float(rng.uniform(35.0, 75.0)),
                esg_score=float(rng.uniform(45.0, 88.0)),
                region=region,
                assigned_team="Reporting Ops",
                latency_ms=_base_latency_ms("reporting", "healthy", rng),
                integration_status="healthy",
                anomaly_flag=False,
                notes="scheduled investor reporting snapshot",
            )

    incident_count = max(8, int(days * 0.35))
    systems = [
        "loan_servicing_api",
        "crm_sync",
        "payment_gateway",
        "underwriting_api",
        "esg_vendor_feed",
        "investor_reporting_export",
    ]
    for incident_idx in range(incident_count):
        incident_time = start_time + timedelta(hours=float(rng.uniform(0.0, days * 24.0)))
        affected_system = str(rng.choice(systems))
        failure_latency = float(rng.uniform(1800.0, 9000.0))

        _append_event(
            records,
            timestamp=incident_time,
            source_system="integration_hub",
            entity_type="integration",
            entity_id=f"INC-{incident_idx + 1:04d}",
            customer_id="platform",
            workflow_stage="servicing",
            workflow_status="failed",
            event_type="integration_failure",
            transaction_amount=0.0,
            payment_status="not_applicable",
            risk_score=float(rng.uniform(40.0, 90.0)),
            esg_score=float(rng.uniform(40.0, 80.0)),
            region=str(rng.choice(REGIONS)),
            assigned_team="Platform Integrations",
            latency_ms=failure_latency,
            integration_status="failed",
            anomaly_flag=True,
            notes=f"incident in {affected_system}",
        )

        _append_event(
            records,
            timestamp=incident_time + timedelta(minutes=float(rng.uniform(30.0, 320.0))),
            source_system="integration_hub",
            entity_type="integration",
            entity_id=f"INC-{incident_idx + 1:04d}",
            customer_id="platform",
            workflow_stage="servicing",
            workflow_status="completed",
            event_type="integration_recovered",
            transaction_amount=0.0,
            payment_status="not_applicable",
            risk_score=float(rng.uniform(35.0, 85.0)),
            esg_score=float(rng.uniform(40.0, 80.0)),
            region=str(rng.choice(REGIONS)),
            assigned_team="Platform Integrations",
            latency_ms=float(rng.uniform(220.0, 640.0)),
            integration_status="recovering",
            anomaly_flag=False,
            notes=f"recovery completed for {affected_system}",
        )

    raw = pd.DataFrame(records)

    if "workflow_stage" in raw.columns:
        raw.loc[raw.sample(frac=0.02, random_state=seed).index, "workflow_stage"] = raw["workflow_stage"].str.upper()
    if "integration_status" in raw.columns:
        raw.loc[raw.sample(frac=0.015, random_state=seed + 11).index, "integration_status"] = "DEGRADED "
    if "event_type" in raw.columns:
        raw.loc[raw.sample(frac=0.02, random_state=seed + 23).index, "event_type"] = (
            raw["event_type"].astype(str) + " "
        )

    raw = raw.sample(frac=1.0, random_state=seed + 99).reset_index(drop=True)
    return normalize_event_dataframe(raw)

#!/usr/bin/env python3
"""Exact front-zone score covariance from fixed lottery ticket portfolios."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

MODELS = ("A", "B1", "B2", "C", "D")
CANDIDATES = ("A", "B1", "B2", "C")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def current_source_hash() -> str:
    digest = hashlib.sha256()
    for path in sorted(Path("src").glob("*.py")):
        digest.update(path.name.encode("utf-8") + b"\0" + path.read_bytes())
    return digest.hexdigest()


def validate_front_portfolio(tickets, expected_count=10, n_numbers=35, ticket_size=5):
    if not isinstance(tickets, list) or len(tickets) != expected_count:
        raise ValueError(f"portfolio must contain exactly {expected_count} tickets")
    seen = set()
    for ticket in tickets:
        if not isinstance(ticket, dict):
            raise ValueError("ticket must be an object")
        front = ticket.get("front")
        if not isinstance(front, list) or len(front) != ticket_size:
            raise ValueError("front zone must contain exactly five numbers")
        if any(type(x) is not int or not 1 <= x <= n_numbers for x in front):
            raise ValueError("front number outside legal integer range")
        if len(set(front)) != ticket_size:
            raise ValueError("duplicate number within a front zone")
        key = tuple(sorted(front))
        if key in seen:
            raise ValueError("duplicate ticket within model portfolio")
        seen.add(key)
    return True


def exposure_vector(tickets, n_numbers=35, expected_count=10):
    validate_front_portfolio(tickets, expected_count, n_numbers, 5)
    counts = [0] * n_numbers
    for ticket in tickets:
        for number in ticket["front"]:
            counts[number - 1] += 1
    return counts


def score_mean(exposure, draw_size=5, ticket_count=10):
    return draw_size * sum(exposure) / (len(exposure) * ticket_count)


def score_covariance(exposure_a, exposure_b, draw_size=5, ticket_count=10):
    """Exact covariance of two portfolio mean-hit scores under uniform draws."""
    if len(exposure_a) != len(exposure_b) or len(exposure_a) < 2:
        raise ValueError("exposure vectors must have equal length >= 2")
    n_numbers = len(exposure_a)
    if not 1 <= draw_size < n_numbers:
        raise ValueError("draw_size must be between 1 and N-1")
    if ticket_count <= 0:
        raise ValueError("ticket_count must be positive")
    mean_a = sum(exposure_a) / n_numbers
    mean_b = sum(exposure_b) / n_numbers
    centered_product = sum(
        (a - mean_a) * (b - mean_b)
        for a, b in zip(exposure_a, exposure_b)
    )
    factor = draw_size * (n_numbers - draw_size) / (
        n_numbers * (n_numbers - 1) * ticket_count * ticket_count
    )
    return factor * centered_product


def covariance_matrix(exposures, draw_size=5, ticket_count=10):
    names = list(exposures)
    matrix = []
    for name_a in names:
        row = []
        for name_b in names:
            row.append(score_covariance(
                exposures[name_a], exposures[name_b], draw_size, ticket_count
            ))
        matrix.append(row)
    return names, matrix


def paired_difference_covariance(model_cov, names, control="D", candidates=CANDIDATES):
    index = {name: i for i, name in enumerate(names)}
    if control not in index or any(name not in index for name in candidates):
        raise ValueError("model covariance matrix is missing a required model")
    d = index[control]
    out = []
    for model_a in candidates:
        ia = index[model_a]
        row = []
        for model_b in candidates:
            ib = index[model_b]
            value = (
                model_cov[ia][ib] - model_cov[ia][d]
                - model_cov[d][ib] + model_cov[d][d]
            )
            row.append(value)
        out.append(row)
    return out


def analyze_payload(payload):
    if payload.get("experiment_id") != "DLT-PI-200":
        raise ValueError("payload experiment_id is not DLT-PI-200")
    if not isinstance(payload.get("draw_id"), str) or not payload["draw_id"].strip():
        raise ValueError("payload draw_id must be a non-empty string")
    if payload.get("models") != list(MODELS) or payload.get("tickets_per_model") != 10:
        raise ValueError("payload model registry or ticket budget does not match the frozen design")
    provenance_fields=("code_sha256","analysis_plan_sha256","pi_source_sha256",
                       "historical_snapshot_sha256","history_audit_sha256",
                       "history_snapshot_completed_at_utc","historical_draw_count","game_rules_id")
    missing=[key for key in provenance_fields if not payload.get(key)]
    if missing:
        raise ValueError("payload missing frozen provenance fields: "+", ".join(missing))
    if not isinstance(payload.get("parameters"),dict):
        raise ValueError("payload is missing frozen model parameters")
    audit=payload.get("history_audit")
    if not isinstance(audit,dict) or audit.get("status")!="PASS" or audit.get("errors") or audit.get("warnings"):
        raise ValueError("payload history audit must be PASS with no errors or warnings")
    if audit.get("continuity_status")!="VERIFIED_AGAINST_OFFICIAL_CALENDAR" or not audit.get("calendar_attestation_sha256"):
        raise ValueError("payload history audit lacks verified official calendar continuity")
    audit_bytes=json.dumps(audit,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
    if hashlib.sha256(audit_bytes).hexdigest()!=payload.get("history_audit_sha256"):
        raise ValueError("payload history audit hash mismatch")
    if audit.get("csv_sha256_computed")!=payload.get("historical_snapshot_sha256"):
        raise ValueError("history audit CSV hash does not match payload snapshot")
    if audit.get("draw_count")!=payload.get("historical_draw_count"):
        raise ValueError("history audit row count does not match payload")
    if audit.get("snapshot_completed_at_utc")!=payload.get("history_snapshot_completed_at_utc"):
        raise ValueError("history audit timestamp does not match payload snapshot")
    tickets = payload.get("tickets")
    if not isinstance(tickets, dict) or set(tickets) != set(MODELS):
        raise ValueError("payload must contain exactly A,B1,B2,C,D")
    exposures = {model: exposure_vector(tickets[model]) for model in MODELS}
    names, model_cov = covariance_matrix(exposures)
    diff_cov = paired_difference_covariance(model_cov, names)
    exposure_summary = {}
    for model, values in exposures.items():
        mean = sum(values) / len(values)
        exposure_summary[model] = {
            "sum": sum(values),
            "unique_numbers_used": sum(v > 0 for v in values),
            "max_number_exposure": max(values),
            "min_number_exposure": min(values),
            "centered_exposure_ss": sum((v - mean) ** 2 for v in values),
            "expected_front_hits_per_ticket": score_mean(values),
        }
    return {
        "draw_id": payload.get("draw_id"),
        "models": list(MODELS),
        "exposure_summary": exposure_summary,
        "score_covariance_matrix": model_cov,
        "paired_difference_models": list(CANDIDATES),
        "paired_difference_covariance_matrix": diff_cov,
    }


def analyze_panel(payloads):
    if len(payloads) != 200:
        raise ValueError("confirmatory power panel must contain exactly 200 draw payloads")
    draw_ids = [p.get("draw_id") for p in payloads]
    if any(not isinstance(x, str) or not x.strip() for x in draw_ids):
        raise ValueError("every panel payload must have a non-empty draw_id")
    if len(set(draw_ids)) != len(draw_ids):
        raise ValueError("portfolio panel contains duplicate draw_id values")
    provenance_fields=("code_sha256","analysis_plan_sha256","pi_source_sha256",
                       "historical_snapshot_sha256","history_audit_sha256",
                       "history_snapshot_completed_at_utc","historical_draw_count","game_rules_id")
    baseline={key:payloads[0].get(key) for key in provenance_fields}
    if baseline["code_sha256"]!=current_source_hash():
        raise ValueError("portfolio panel source code hash does not match current frozen src/ tree")
    prereg=Path("PREREGISTRATION.md")
    if prereg.exists() and baseline["analysis_plan_sha256"]!=sha(prereg.read_bytes()):
        raise ValueError("portfolio panel analysis-plan hash does not match current PREREGISTRATION.md")
    baseline_parameters=json.dumps(payloads[0].get("parameters"),sort_keys=True,separators=(",",":"))
    for payload in payloads[1:]:
        for key in provenance_fields:
            if payload.get(key)!=baseline[key]:
                raise ValueError(f"portfolio panel mixes frozen provenance field: {key}")
        if json.dumps(payload.get("parameters"),sort_keys=True,separators=(",",":"))!=baseline_parameters:
            raise ValueError("portfolio panel mixes model parameter definitions")
    draw_reports = [analyze_payload(p) for p in payloads]
    names = list(CANDIDATES)
    avg_cov = [[
        sum(r["paired_difference_covariance_matrix"][i][j] for r in draw_reports) / len(draw_reports)
        for j in range(len(names))
    ] for i in range(len(names))]
    cov_of_mean = [[x / len(draw_reports) for x in row] for row in avg_cov]
    return {
        "experiment_id": "DLT-PI-200",
        "draw_count": len(draw_reports),
        "independent_unit": "draw",
        "paired_difference_models": names,
        "frozen_provenance": baseline,
        "parameters_sha256": hashlib.sha256(baseline_parameters.encode()).hexdigest(),
        "average_per_draw_paired_difference_covariance": avg_cov,
        "covariance_of_200_draw_mean": cov_of_mean,
        "draw_level_diagnostics": draw_reports,
        "status": "COMPUTED_FROM_FIXED_PORTFOLIOS_UNDER_UNIFORM_DRAW_NULL",
        "limitation": "Exact conditional moments under uniform 5-of-35 draws; does not model non-uniform draw mechanisms or prove predictive edge."
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--payload", action="append", default=[])
    ap.add_argument("--panel-jsonl")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    if args.panel_jsonl:
        payloads = [
            json.loads(line) for line in Path(args.panel_jsonl).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        result = analyze_panel(payloads)
    else:
        if len(args.payload) != 1:
            ap.error("provide exactly one --payload or one --panel-jsonl")
        result = analyze_payload(json.loads(Path(args.payload[0]).read_text(encoding="utf-8")))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"] if "status" in result else "COMPUTED",
                      "output": str(out)}, indent=2))


if __name__ == "__main__":
    main()

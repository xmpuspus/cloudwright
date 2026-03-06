from __future__ import annotations

import dataclasses


def security_report_to_dict(report) -> dict:
    return {
        "passed": report.passed,
        "critical_count": report.critical_count,
        "high_count": report.high_count,
        "findings": [dataclasses.asdict(f) for f in report.findings],
    }


def lint_warnings_to_dict(warnings) -> list[dict]:
    return [dataclasses.asdict(w) for w in warnings]


def score_result_to_dict(result) -> dict:
    return result.to_dict()


def analysis_result_to_dict(result) -> dict:
    return result.to_dict()

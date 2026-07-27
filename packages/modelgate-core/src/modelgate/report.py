"""The Report — schema matches specs/mgs/MGS-1.0-draft.md §4."""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

Verdict = Literal["PASS", "FAIL", "NOT_EVALUATED", "PARTIAL"]


@dataclass
class RequirementResult:
    id: str
    verdict: Verdict
    config: dict[str, Any]
    metrics: dict[str, Any]
    findings: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Report:
    spec_version: str
    tool_version: str
    dataset_hash: str
    generated_at: str
    requirements: list[RequirementResult]
    informative: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def verdict_for(self, requirement_id: str) -> Verdict | None:
        for r in self.requirements:
            if r.id == requirement_id:
                return r.verdict
        return None

    @property
    def overall_verdict(self) -> Verdict:
        """FAIL if any Requirement FAILed; NOT_EVALUATED if none FAILed but
        at least one couldn't be evaluated; PASS only if every Requirement
        PASSed. Never a silent default — this itself follows MGS-0000."""
        verdicts = {r.verdict for r in self.requirements}
        if "FAIL" in verdicts:
            return "FAIL"
        if "NOT_EVALUATED" in verdicts or "PARTIAL" in verdicts:
            return "NOT_EVALUATED"
        return "PASS"


def now_iso8601_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

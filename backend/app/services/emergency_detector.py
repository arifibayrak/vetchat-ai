"""
Emergency detector — runs BEFORE any LLM call.
Pure Python with zero external dependencies beyond the stdlib.
"""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_KEYWORDS_PATH = Path(__file__).parent.parent / "data" / "emergency_keywords.json"

EMERGENCY_RESOURCES = [
    "ASPCA Animal Poison Control Center (toxicology consultation): (888) 426-4435 — 24/7",
    "ASPCA Pro Veterinary Toxicology resources: aspca.pro",
    "Activate in-clinic emergency stabilisation protocol immediately",
    "Consider specialist referral (internal medicine, toxicology, emergency/critical care) as indicated",
]

DISCLAIMER = (
    "VetChat AI is a clinical reference tool for licensed veterinary professionals. "
    "Information is derived from peer-reviewed veterinary literature and is intended "
    "to support — not replace — clinical judgment. All treatment decisions must account "
    "for patient-specific factors and applicable professional standards of care."
)


@dataclass
class EmergencyResult:
    is_emergency: bool
    category: str | None = None
    matched_term: str | None = None
    message: str | None = None
    resources: list[str] = field(default_factory=list)


class EmergencyDetector:
    def __init__(self, keywords_path: Path = _KEYWORDS_PATH) -> None:
        with open(keywords_path) as f:
            data = json.load(f)

        self._categories: dict[str, dict] = data["categories"]

        # Pre-compile regex patterns per category
        self._compiled: dict[str, list[re.Pattern]] = {}
        for cat, cfg in self._categories.items():
            self._compiled[cat] = [
                re.compile(p) for p in cfg.get("patterns", [])
            ]

    def check(self, query: str) -> EmergencyResult:
        lowered = query.lower()

        for cat, cfg in self._categories.items():
            # Keyword scan (word-boundary aware for multi-word phrases)
            for kw in cfg.get("keywords", []):
                if kw in lowered:
                    return EmergencyResult(
                        is_emergency=True,
                        category=cat,
                        matched_term=kw,
                        message=cfg["message"],
                        resources=EMERGENCY_RESOURCES,
                    )

            # Regex pattern scan
            for pattern in self._compiled[cat]:
                m = pattern.search(query)
                if m:
                    return EmergencyResult(
                        is_emergency=True,
                        category=cat,
                        matched_term=m.group(0),
                        message=cfg["message"],
                        resources=EMERGENCY_RESOURCES,
                    )

        return EmergencyResult(is_emergency=False)


# Module-level singleton
_detector: EmergencyDetector | None = None


def get_detector() -> EmergencyDetector:
    global _detector
    if _detector is None:
        _detector = EmergencyDetector()
    return _detector

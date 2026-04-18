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

EMERGENCY_PRELIMINARY: dict[str, dict] = {
    "toxicology": {
        "heading": "Toxicology Emergency — Immediate Actions",
        "priorities": [
            "Identify the toxin and dose ingested (owner history, product label, time of exposure)",
            "Call ASPCA Animal Poison Control: (888) 426-4435 — 24/7 for species-specific decontamination guidance",
            "Induce emesis only if: <2h post-ingestion, patient is alert and asymptomatic, and toxin warrants it — do NOT induce for corrosives, hydrocarbons, or CNS toxins",
            "Establish IV access; collect baseline bloods (CBC, biochemistry, coagulation profile)",
            "Administer activated charcoal if indicated per toxin type (not for ethanol, heavy metals, corrosives)",
            "Monitor continuously: HR, RR, temperature, mucous membrane colour, mentation, and urinary output",
        ],
    },
    "respiratory": {
        "heading": "Respiratory Emergency — Immediate Actions",
        "priorities": [
            "Place in oxygen cage or provide flow-by O₂ immediately — prioritise oxygenation above all else",
            "Minimise stress and handling — do NOT restrain for diagnostics until the patient is stabilised",
            "Assess: respiratory rate and effort, MM colour (cyanosis = critical), and auscultate bilaterally",
            "If pleural effusion or pneumothorax suspected: prepare for emergency thoracocentesis",
            "Establish IV/IO access once patient tolerates handling; collect blood gas if available",
            "Lateral thoracic radiograph only once oxygenation is adequate and patient is stable enough",
        ],
    },
    "cardiovascular": {
        "heading": "Cardiovascular Emergency — Immediate Actions",
        "priorities": [
            "Assess perfusion immediately: MM colour, CRT, pulse quality, heart rate, and blood pressure",
            "Provide supplemental O₂ (flow-by or mask); prepare crash cart — be ready for CPR if pulseless",
            "Establish two large-bore IV catheters; initiate fluid resuscitation per haemodynamic status",
            "Attach ECG immediately — identify arrhythmia type before drug intervention",
            "If cardiac tamponade suspected (muffled heart sounds, pulsus paradoxus): prepare for pericardiocentesis",
            "Emergency echocardiogram if available — rule out pericardial effusion and structural disease",
        ],
    },
    "trauma": {
        "heading": "Trauma Emergency — Immediate Actions",
        "priorities": [
            "Primary survey: Airway → Breathing → Circulation — identify and address life threats in order",
            "Control external haemorrhage with direct pressure; tourniquet for uncontrolled limb haemorrhage",
            "Establish IV access; crystalloid resuscitation cautiously — avoid aggressive fluids with suspected internal haemorrhage",
            "Opioid analgesia (e.g. methadone or butorphanol) once haemodynamics allow — do not delay adequate pain relief",
            "Thoracic auscultation — rule out tension pneumothorax or haemothorax requiring immediate intervention",
            "Secondary survey and imaging (thoracic/abdominal radiographs) once cardiovascular status is stabilised",
        ],
    },
    "neurological": {
        "heading": "Neurological Emergency — Immediate Actions",
        "priorities": [
            "Protect the patient from self-injury: padded area, remove obstacles, do NOT restrain head during active seizure",
            "If seizing >5 minutes (status epilepticus): diazepam IV/PR 0.5 mg/kg or midazolam IM/IN 0.2 mg/kg",
            "Measure blood glucose immediately — hypoglycaemia is rapidly treatable and must be excluded first",
            "Establish IV access; collect blood for glucose, electrolytes, BUN, calcium, and CBC",
            "If cluster seizures persist after benzodiazepine: phenobarbital IV loading dose per current formulary",
            "Full neurological localisation examination once seizures are controlled; MRI recommended if structural lesion suspected",
        ],
    },
    "acute_abdomen": {
        "heading": "Acute Abdomen Emergency — Immediate Actions",
        "priorities": [
            "Establish two large-bore IV catheters immediately; begin aggressive crystalloid resuscitation",
            "Lateral and VD abdominal radiographs: assess for GDV (double-bubble sign), free gas, obstruction, or displaced viscera",
            "If GDV confirmed: gastric decompression (orogastric tube or trocarisation) before surgical preparation",
            "Urethral obstruction: pass urethral catheter urgently; treat life-threatening hyperkalaemia before anaesthesia",
            "Opioid analgesia once IV access established — avoid NSAIDs with haemodynamic compromise or suspected perforation",
            "Surgical consultation immediately — GDV, intestinal obstruction, bile peritonitis, and haemoabdomen require emergency laparotomy",
        ],
    },
}

DISCLAIMER = (
    "Arlo is a clinical reference tool for licensed veterinary professionals. "
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
    preliminary: dict | None = None


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
                        preliminary=EMERGENCY_PRELIMINARY.get(cat),
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
                        preliminary=EMERGENCY_PRELIMINARY.get(cat),
                    )

        return EmergencyResult(is_emergency=False)


# Module-level singleton
_detector: EmergencyDetector | None = None


def get_detector() -> EmergencyDetector:
    global _detector
    if _detector is None:
        _detector = EmergencyDetector()
    return _detector

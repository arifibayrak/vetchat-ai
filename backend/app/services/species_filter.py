"""
Species-aware post-retrieval filter.
Reorders retrieved results so species-matched sources appear first and
clearly human-medicine-only sources are deprioritised to the end.
No results are deleted — all evidence is preserved.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import TypeVar

T = TypeVar("T")


class Species(str, Enum):
    CANINE  = "canine"
    FELINE  = "feline"
    EQUINE  = "equine"
    AVIAN   = "avian"
    BOVINE  = "bovine"
    EXOTIC  = "exotic"
    MIXED   = "mixed"
    UNKNOWN = "unknown"


_SPECIES_PATTERNS: dict[Species, list[str]] = {
    Species.CANINE: [
        r"\bdog\b", r"\bdogs\b", r"\bcanine\b", r"\bcanines\b",
        r"\bpuppy\b", r"\bpuppies\b", r"\bwhelp\b",
    ],
    Species.FELINE: [
        r"\bcat\b", r"\bcats\b", r"\bfeline\b", r"\bfelines\b",
        r"\bkitten\b", r"\bkittens\b",
    ],
    Species.EQUINE: [
        r"\bhorse\b", r"\bhorses\b", r"\bequine\b", r"\bmare\b",
        r"\bfoal\b", r"\bstallion\b", r"\bgelding\b", r"\bpony\b",
    ],
    Species.AVIAN: [
        r"\bbird\b", r"\bbirds\b", r"\bavian\b", r"\bparrot\b",
        r"\bpoultry\b", r"\braptor\b", r"\bchicken\b", r"\bpigeon\b",
    ],
    Species.BOVINE: [
        r"\bcow\b", r"\bcows\b", r"\bbovine\b", r"\bcattle\b",
        r"\bbull\b", r"\bcalf\b", r"\bheifer\b",
    ],
    Species.EXOTIC: [
        r"\brabbit\b", r"\bferret\b", r"\bguinea pig\b", r"\breptile\b",
        r"\bhamster\b", r"\bchinchilla\b", r"\bhedgehog\b", r"\btortoise\b",
        r"\bbearded dragon\b",
    ],
}

# Signals that strongly indicate human-medicine context — used to deprioritise, not delete.
# Kept conservative to avoid false positives (e.g. "patient" alone is too broad for vet lit).
_HUMAN_SIGNALS: list[str] = [
    r"\bhuman subjects\b", r"\bhuman patients\b", r"\bhuman studies\b",
    r"\bobstetric\b", r"\bmaternal\b", r"\bgestational\b", r"\bpostpartum\b",
    r"\bneonatal intensive\b", r"\bpediatric patient\b", r"\bpediatric ward\b",
    r"\bICU patient\b", r"\bnursing home\b", r"\bclinical trial.*human\b",
]

_COMPILED_SPECIES: dict[Species, list[re.Pattern]] = {
    sp: [re.compile(p, re.IGNORECASE) for p in patterns]
    for sp, patterns in _SPECIES_PATTERNS.items()
}
_COMPILED_HUMAN: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in _HUMAN_SIGNALS
]


def detect_species(query: str) -> Species:
    """Detect the primary species mentioned in the user query."""
    found: list[Species] = []
    for sp, patterns in _COMPILED_SPECIES.items():
        if any(p.search(query) for p in patterns):
            found.append(sp)
    if len(found) == 0:
        return Species.UNKNOWN
    if len(found) == 1:
        return found[0]
    return Species.MIXED


def _score(text: str, species: Species) -> int:
    """
    Score a result for relevance to the detected species.
      2 = species keyword found in text (prioritise)
      1 = neutral (no species cue either way)
      0 = human-medicine signals found and no species cue (deprioritise)
    """
    has_species = any(
        p.search(text) for p in _COMPILED_SPECIES.get(species, [])
    )
    if has_species:
        return 2
    is_human = any(p.search(text) for p in _COMPILED_HUMAN)
    return 0 if is_human else 1


def filter_and_reorder(
    resources: list[T],
    species: Species,
    get_text: "callable[[T], str]",
) -> list[T]:
    """
    Stable-sort resources so species-matched results come first and
    human-medicine-only results come last. Never removes any result.
    Returns the list unchanged when species is UNKNOWN or MIXED.
    """
    if species in (Species.UNKNOWN, Species.MIXED):
        return resources

    scored = [(r, _score(get_text(r), species)) for r in resources]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [r for r, _ in scored]

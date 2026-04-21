"""
Toxicology query intent detection.

The retrieval pipeline is generic, but toxicology queries hit three specific
failure modes today:

  1. Corpus gap — T&F journals have almost zero tox content, so even with
     perfect retrieval there's little to find. (Fixed separately by running
     `ingest_crossref_tox.py`.)
  2. Ranking prior — tox-dedicated journals (JVECC, Clinical Toxicology,
     JMedTox) should get a small bump over incidental matches from general
     veterinary journals so the reranker's top-k tilts toward the right
     outlets when evidence is sparse.
  3. Query breadth — "lily toxicosis" is a narrow term; we want to fetch
     more candidates pre-rerank for tox queries so the reranker has more
     material to work with.

This module provides a cheap keyword-whitelist detector that the chat
handler uses to tune retrieval behavior when a tox query is in-flight.
"""
from __future__ import annotations

import re
from typing import Literal

# Canonical tox vocabulary. Aligned with `_TOX_KEYWORDS` in
# `scripts/ingest_crossref_tox.py` so the detector catches the same
# queries the ingest pipeline was scoped for.
_TOX_TERMS: frozenset[str] = frozenset({
    # Iconic small-animal toxins
    "xylitol", "chocolate", "theobromine", "methylxanthine",
    "grape", "raisin", "allium", "onion", "garlic", "leek",
    "lily", "lilium",
    "acetaminophen", "paracetamol", "ibuprofen", "naproxen", "aspirin",
    "nsaid",
    "ethylene glycol", "antifreeze",
    "rodenticide", "anticoagulant rodenticide", "bromethalin", "brodifacoum",
    "permethrin", "pyrethroid",
    "metaldehyde", "slug bait",
    "strychnine", "organophosphate", "carbamate",
    "lead toxicity", "zinc toxicity",
    # Disease / presentation terms common in tox literature
    "toxicity", "toxicosis", "toxicology", "poisoning", "intoxication",
    "envenomation", "envenoming", "snake bite", "scorpion",
    "hepatotoxic", "nephrotoxic", "neurotoxic", "cardiotoxic",
    # Generic tox suffixes
    "toxin", "toxicant",
})

# Curated journal list that should get a small ranking prior on tox queries.
# Matches exact `journal` metadata values the Crossref ingest writes to Chroma.
TOX_JOURNAL_NAMES: frozenset[str] = frozenset({
    "Journal of Veterinary Emergency and Critical Care",
    "Journal of Medical Toxicology",
    "Clinical Toxicology",
    "Toxicology",
    "Toxicology Reports",
    "Toxicology and Applied Pharmacology",
    "Toxicologic Pathology",
    "Veterinary and Comparative Oncology",
})

Intent = Literal["toxicology", "emergency", "general"]


def is_tox_query(query: str) -> bool:
    """True if the query mentions at least one tox-specific term."""
    lowered = (query or "").lower()
    return any(term in lowered for term in _TOX_TERMS)


# Species qualifier presence — helps distinguish "xylitol pharmacology"
# (human pharma research) from "xylitol ingestion dog" (real vet case).
_SPECIES_HINTS = re.compile(
    r"\b(dog|canine|cat|feline|puppy|kitten|horse|equine|rabbit|ferret|"
    r"bird|avian|bovine|cow|calf|veterinary|vet)\b",
    re.I,
)


def classify_intent(query: str, emergency_category: str | None) -> Intent:
    """
    Return the retrieval intent for this query.

    Priority:
      1. If the emergency detector flagged category == "toxicology", return
         "toxicology" (strongest signal — an active case needing tox-specific
         retrieval tuning).
      2. If the query contains tox vocabulary AND a species hint, return
         "toxicology". The species hint keeps us from routing generic-pharma
         questions to the vet-tox corpus.
      3. If the emergency detector flagged any other category, return
         "emergency".
      4. Otherwise "general".
    """
    if emergency_category == "toxicology":
        return "toxicology"
    if is_tox_query(query) and _SPECIES_HINTS.search(query or ""):
        return "toxicology"
    if emergency_category:
        return "emergency"
    return "general"


def is_tox_journal(journal: str) -> bool:
    """True if the journal name is on the curated tox-outlet list."""
    if not journal:
        return False
    # Exact match first
    if journal in TOX_JOURNAL_NAMES:
        return True
    # Substring fallback (the Crossref response can append ", The" etc.)
    lowered = journal.lower()
    return any(name.lower() in lowered for name in TOX_JOURNAL_NAMES)

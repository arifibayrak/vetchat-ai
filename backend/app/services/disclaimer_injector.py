from app.services.emergency_detector import DISCLAIMER

_DISCLAIMER_BLOCK = f"\n\n---\n**Disclaimer:** {DISCLAIMER}"


def inject(answer: str) -> str:
    """Append the standard veterinary disclaimer to an LLM answer."""
    return answer + _DISCLAIMER_BLOCK

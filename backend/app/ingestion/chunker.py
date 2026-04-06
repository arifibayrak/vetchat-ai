"""
Sentence-boundary aware text chunker.
Target: 512 tokens, 64-token overlap, 128-token minimum.
"""
import re
import tiktoken

_TOKENIZER = tiktoken.get_encoding("cl100k_base")
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')

TARGET_TOKENS = 512
OVERLAP_TOKENS = 64
MIN_TOKENS = 128


def _tokenize(text: str) -> list[int]:
    return _TOKENIZER.encode(text)


def _detokenize(tokens: list[int]) -> str:
    return _TOKENIZER.decode(tokens)


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks respecting sentence boundaries."""
    sentences = _SENTENCE_SPLIT.split(text)
    # Merge very short fragments back into previous sentence
    merged: list[str] = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if merged and len(_tokenize(sent)) < 5:
            merged[-1] = merged[-1] + " " + sent
        else:
            merged.append(sent)

    chunks: list[str] = []
    current_tokens: list[int] = []

    for sentence in merged:
        sent_tokens = _tokenize(sentence)

        # If adding this sentence exceeds the target, flush
        if len(current_tokens) + len(sent_tokens) > TARGET_TOKENS and len(current_tokens) >= MIN_TOKENS:
            chunks.append(_detokenize(current_tokens))
            # Keep overlap from the end of the current chunk
            current_tokens = current_tokens[-OVERLAP_TOKENS:]

        current_tokens.extend(sent_tokens)

    # Flush remainder
    if len(current_tokens) >= MIN_TOKENS:
        chunks.append(_detokenize(current_tokens))
    elif chunks and len(current_tokens) > 0:
        # Merge tail into last chunk
        chunks[-1] = chunks[-1] + " " + _detokenize(current_tokens)

    return chunks if chunks else [text]

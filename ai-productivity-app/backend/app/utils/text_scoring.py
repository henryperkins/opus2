
"""Lightweight text-scoring helpers (tokenization + TF-IDF).

This module is extracted from search.hybrid so the calculation can be
re-used across the backend without importing the full hybrid search
implementation.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, List

__all__: list[str] = [
    "tokenize_query",
    "calculate_tf_idf_score",
]

_WORD_RE = re.compile(r"[^\w\s]")

# ---------------------------------------------------------------------------


def tokenize_query(query: str) -> List[str]:
    """Tokenise *query* into lowercase alphanumeric words (≥ 2 chars)."""
    clean_query = _WORD_RE.sub(" ", query.lower())
    return [tok for tok in clean_query.split() if len(tok) > 1]


def calculate_tf_idf_score(
    content: str,
    query_tokens: List[str],
    total_docs: int,
    term_doc_freq: Dict[str, int],
) -> float:
    """Return the TF-IDF similarity score between *content* and *query_tokens*.

    Parameters
    ----------
    content:
        Document text.
    query_tokens:
        Pre-tokenised query terms.
    total_docs:
        Total number of documents in corpus (for IDF calculation).
    term_doc_freq:
        Mapping *token → document-frequency* (documents containing token).
    """
    if not query_tokens:
        return 0.0

    content_tokens = tokenize_query(content.lower())
    if not content_tokens:
        return 0.0

    content_counter = Counter(content_tokens)
    doc_len = len(content_tokens)

    score = 0.0
    for token in query_tokens:
        tf = content_counter.get(token, 0) / doc_len if doc_len else 0.0
        if tf:
            idf = math.log(total_docs / max(term_doc_freq.get(token, 1), 1))
            score += tf * idf

    return score

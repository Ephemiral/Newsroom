"""
Article embedding for the clustering stage.

Uses sentence-transformers (all-MiniLM-L6-v2 by default — fast, free, good
enough for news clustering). Falls back gracefully if the model isn't cached
yet; first run downloads it automatically (~90 MB).

Input:  Article objects
Output: numpy array of L2-normalised embeddings, one row per article
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from pipeline.schema import Article

log = logging.getLogger(__name__)

# Default model — small, fast, strong for semantic similarity
DEFAULT_MODEL = "all-MiniLM-L6-v2"
# Max chars of body text to include (keeps cost/time bounded)
MAX_BODY_CHARS = 500


def _article_text(article: Article) -> str:
    """Combine title + lead of body into a single embedding input."""
    body_lead = (article.body_text or "")[:MAX_BODY_CHARS].strip()
    return f"{article.title}. {body_lead}" if body_lead else article.title


def embed_articles(
    articles: list[Article],
    model_name: str = DEFAULT_MODEL,
) -> tuple[np.ndarray, list[str]]:
    """
    Embed a list of articles.

    Returns:
        embeddings: float32 array of shape (n_articles, embedding_dim),
                    L2-normalised so cosine similarity = dot product.
        article_ids: list of article_id strings, aligned with embedding rows.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError(
            "sentence-transformers is required for clustering. "
            "Install with: pip install sentence-transformers"
        )

    texts = [_article_text(a) for a in articles]
    ids = [a.article_id for a in articles]

    log.info("Loading embedding model: %s", model_name)
    model = SentenceTransformer(model_name)

    log.info("Embedding %d articles...", len(texts))
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=32,
    )
    return np.array(embeddings, dtype=np.float32), ids

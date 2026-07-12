"""
Embedding utilities for the ISIC Rev.5 semantic classification pipeline.

This module provides:
- Lightweight token-based chunking for long text inputs
- Prefixing logic for query/passages (required by multilingual-e5-large)
- Mean-pooled embedding generation across chunks
- Model loader for multilingual-e5-large

The goal is to produce stable, semantically rich embeddings for both
project-level and file-level classification, while keeping memory usage
predictable across large datasets.
"""

from sentence_transformers import SentenceTransformer
import numpy as np

# Default chunk size (approximate token count using word count)
CHUNK_SIZE_TOKENS = 512

# Minimum text length required before embedding
MIN_TEXT_LENGTH = 50

# Embedding model name
EMBED_MODEL_NAME = "intfloat/multilingual-e5-large"

# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def chunk_text(text: str, chunk_size_tokens: int = CHUNK_SIZE_TOKENS) -> list:
    """
    Splits text into ~chunk_size_tokens word chunks.

    Parameters
    ----------
    text : str
        Input text to be chunked.
    chunk_size_tokens : int
        Approximate number of words per chunk.

    Returns
    -------
    list[str]
        List of text chunks.
    """
    words = text.split()
    if len(words) <= chunk_size_tokens:
        return [text]

    chunks = []
    for i in range(0, len(words), chunk_size_tokens):
        chunk_words = words[i : i + chunk_size_tokens]
        chunks.append(" ".join(chunk_words))

    return chunks

# ---------------------------------------------------------------------------
# Embedding with chunking + prefixing
# ---------------------------------------------------------------------------
def embed_text_with_chunks(embedder, text: str, is_query: bool = True):
    """
    Generates a mean-pooled embedding for a text input using chunking.

    Steps:
    - Split text into chunks
    - Prefix each chunk with "query:" or "passage:" (required by e5 models)
    - Encode each chunk
    - Return the mean-pooled embedding

    Parameters
    ----------
    embedder : SentenceTransformer
        Loaded multilingual-e5-large model.
    text : str
        Input text to embed.
    is_query : bool
        Whether to prefix chunks as "query:" or "passage:".

    Returns
    -------
    torch.Tensor or None
        Mean-pooled embedding tensor, or None if text is too short.
    """
    if not text or len(text.strip()) < MIN_TEXT_LENGTH:
        return None

    chunks = chunk_text(text, CHUNK_SIZE_TOKENS)

    prefixed_chunks = []
    for ch in chunks:
        if is_query:
            prefixed_chunks.append(ch if ch.startswith("query: ") else "query: " + ch)
        else:
            prefixed_chunks.append(ch if ch.startswith("passage: ") else "passage: " + ch)

    embeddings = embedder.encode(prefixed_chunks, convert_to_tensor=True)

    # If only one chunk, return directly
    if embeddings.ndim == 1:
        return embeddings

    # Mean pooling across chunks
    return embeddings.mean(dim=0)

# ---------------------------------------------------------------------------
# Model Loader
# ---------------------------------------------------------------------------
def load_embedder():
    """
    Loads the multilingual-e5-large embedding model.

    Returns
    -------
    SentenceTransformer
        Loaded embedding model instance.
    """
    print("Loading multilingual-e5-large embedding model...")
    return SentenceTransformer(EMBED_MODEL_NAME)

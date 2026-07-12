"""
ISIC Rev.5 taxonomy utilities for the semantic classification pipeline.

This module handles:
- Loading ISIC Rev.5 division-level metadata from JSON
- Preparing semantic descriptions for each division
- Precomputing multilingual-e5-large embeddings for all divisions

These embeddings are used during project-level and file-level
classification to compute cosine similarity between extracted text
and ISIC division descriptions.
"""

import os
import sys
import json
from sentence_transformers import SentenceTransformer

from embedder import embed_text_with_chunks
# ---------------------------------------------------------------------------
# Load ISIC Divisions
# ---------------------------------------------------------------------------
def load_isic_divisions(json_path: str) -> list:
    """
    Loads ISIC Rev.5 division metadata from a JSON file.

    Parameters
    ----------
    json_path : str
        Path to the ISIC divisions JSON file.

    Returns
    -------
    list[dict]
        List of ISIC division entries, each containing:
        - code
        - name
        - description
    """
    if not os.path.exists(json_path):
        print(f"ISIC JSON not found: {json_path}")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

# ---------------------------------------------------------------------------
# Precompute ISIC Embeddings
# ---------------------------------------------------------------------------
def precompute_isic_embeddings(embedder: SentenceTransformer, isic_list: list) -> dict:
    """
    Precomputes semantic embeddings for all ISIC divisions.

    Parameters
    ----------
    embedder : SentenceTransformer
        Loaded multilingual-e5-large model.
    isic_list : list[dict]
        ISIC division metadata.

    Returns
    -------
    dict[str, torch.Tensor]
        Mapping from ISIC code → embedding tensor.
    """
    print(f"Precomputing ISIC embeddings ({len(isic_list)} divisions)...")

    isic_emb = {}

    for div in isic_list:
        code = div["code"]
        desc = f"{div.get('name', '')} {div.get('description', '')}"

        emb = embed_text_with_chunks(embedder, desc, is_query=False)
        isic_emb[code] = emb

    return isic_emb

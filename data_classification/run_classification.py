"""
Core ISIC Rev.5 classification routines.

This module implements the main semantic classification logic used in the
pipeline, including:

- Ranking text blocks against ISIC division embeddings
- Project-level classification (metadata + extracted content)
- File-level classification for primary qualitative data
- Database schema initialization for classification outputs
- QDA prioritization and repository-aware project ordering

The functions here operate directly on the SQLite database and rely on
embedding utilities, project text construction, and ISIC taxonomy modules.
"""

import os
import time
import sqlite3
from datetime import datetime

from sentence_transformers import util

from config import (
    MIN_TEXT_LENGTH,
    TOP_K_CANDIDATES,
    PRIMARY_EXTS,
)
from project_text import build_project_text
from extractor import extract_text_from_file
from embedder import embed_text_with_chunks

# ---------------------------------------------------------------------------
# ISIC Similarity Ranking
# ---------------------------------------------------------------------------
def get_top_isic_by_similarity(
    text: str,
    embedder,
    isic_emb: dict,
    isic_list: list,
    k: int = TOP_K_CANDIDATES,
):
    """
    Computes cosine similarity between a text block and all ISIC division
    embeddings, returning the top-k most similar divisions.

    Parameters
    ----------
    text : str
        Project-level or file-level text block.
    embedder : SentenceTransformer
        Loaded multilingual-e5-large model.
    isic_emb : dict[str, torch.Tensor]
        Precomputed ISIC division embeddings.
    isic_list : list[dict]
        ISIC division metadata.
    k : int
        Number of top candidates to return.

    Returns
    -------
    tuple
        (primary_code, primary_name, secondary_code, secondary_name, top_k_list)
    """
    if not text or len(text.strip()) < MIN_TEXT_LENGTH:
        # Fallback: return first two ISIC divisions
        return (
            isic_list[0]["code"],
            isic_list[0]["name"],
            isic_list[1]["code"],
            isic_list[1]["name"],
            [],
        )

    proj_emb = embed_text_with_chunks(embedder, text, is_query=True)
    if proj_emb is None:
        return (
            isic_list[0]["code"],
            isic_list[0]["name"],
            isic_list[1]["code"],
            isic_list[1]["name"],
            [],
        )

    similarities = []
    for div in isic_list:
        code = div["code"]
        if isic_emb[code] is None:
            continue

        sim = util.cos_sim(proj_emb, isic_emb[code]).item()
        similarities.append(
            {
                "code": code,
                "name": div.get("name", ""),
                "similarity": float(sim),
            }
        )

    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    top_k = similarities[:k]

    if not top_k:
        return (
            isic_list[0]["code"],
            isic_list[0]["name"],
            isic_list[1]["code"],
            isic_list[1]["name"],
            [],
        )

    primary = top_k[0]
    secondary = top_k[1] if len(top_k) > 1 else top_k[0]

    return (
        primary["code"],
        primary["name"],
        secondary["code"],
        secondary["name"],
        top_k,
    )

# ---------------------------------------------------------------------------
# File-Level Classification
# ---------------------------------------------------------------------------
def classify_primary_files(
    cur,
    conn,
    project_id,
    downloads_folder,
    isic_list,
    embedder,
    isic_emb,
):
    """
    Classifies each primary qualitative data file in a project.

    Parameters
    ----------
    cur : sqlite3.Cursor
        Database cursor.
    conn : sqlite3.Connection
        Database connection.
    project_id : int
        Project identifier.
    downloads_folder : str
        Root folder containing downloaded files.
    isic_list : list[dict]
        ISIC division metadata.
    embedder : SentenceTransformer
        Loaded multilingual-e5-large model.
    isic_emb : dict[str, torch.Tensor]
        Precomputed ISIC division embeddings.
    """
    # Ensure file_classification table exists
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS file_classification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            file_name TEXT,
            primary_class TEXT,
            secondary_class TEXT,
            similarity_score REAL
        )
        """
    )

    # Fetch project folder structure
    cur.execute(
        """
        SELECT download_repository_folder, download_project_folder
        FROM projects
        WHERE id = ?
        """,
        (project_id,),
    )
    row = cur.fetchone()
    if not row:
        return

    repo_folder, proj_folder = row

    # Fetch primary files
    cur.execute(
        """
        SELECT file_name, file_type, status
        FROM files
        WHERE project_id = ?
          AND status = 'SUCCEEDED'
          AND file_type IN ({})
        """.format(",".join(f"'{ext}'" for ext in PRIMARY_EXTS)),
        (project_id,),
    )
    rows = cur.fetchall()

    if not rows:
        return

    print(f"      - {len(rows)} primary file(s)")

    # Classify each file
    for file_name, file_type, status in rows:
        full_path = os.path.join(
            downloads_folder,
            repo_folder,
            proj_folder,
            file_name,
        )

        text = extract_text_from_file(full_path)
        if not text or len(text.strip()) < MIN_TEXT_LENGTH:
            print(f"        {file_name}: insufficient text")
            continue

        primary, prim_name, secondary, sec_name, top_k = get_top_isic_by_similarity(
            text,
            embedder,
            isic_emb,
            isic_list,
            TOP_K_CANDIDATES,
        )

        sim_score = top_k[0]["similarity"] if top_k else 0.0

        cur.execute(
            """
            INSERT INTO file_classification
                (project_id, file_name, primary_class, secondary_class, similarity_score)
            VALUES (?, ?, ?, ?, ?)
            """,
            (project_id, file_name, primary, secondary, sim_score),
        )
        conn.commit()

        print(f"        {file_name}: {primary} (score: {sim_score:.3f})")

# ---------------------------------------------------------------------------
# Database Schema Initialization
# ---------------------------------------------------------------------------
def init_database_schema(db_path: str):
    """
    Ensures the projects table contains all required classification columns.

    Adds:
    - primary_class
    - secondary_class
    - similarity_score
    - has_qda_files
    - classified_at
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("PRAGMA table_info(projects)")
    existing_cols = {row[1] for row in cur.fetchall()}

    new_cols = {
        "primary_class": "TEXT",
        "secondary_class": "TEXT",
        "similarity_score": "REAL",
        "has_qda_files": "INTEGER",
        "classified_at": "TEXT",
    }

    for col, typ in new_cols.items():
        if col not in existing_cols:
            cur.execute(f"ALTER TABLE projects ADD COLUMN {col} {typ}")
            print(f"Added column: {col}")

    conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# Main Classification Loop
# ---------------------------------------------------------------------------
def run_isic_classification(
    db_path: str,
    downloads_folder: str,
    isic_list: list,
    embedder,
    isic_emb: dict,
):
    """
    Executes project-level and file-level ISIC classification.

    Projects are ordered by:
    1. PROJECT_TYPE priority (QDA_PROJECT → QD_PROJECT → OTHER_PROJECT → UNKNOWN)
    2. Repository priority (Zenodo → DANS → Others)
    3. Project ID

    Parameters
    ----------
    db_path : str
        Path to SQLite database.
    downloads_folder : str
        Root folder containing downloaded files.
    isic_list : list[dict]
        ISIC division metadata.
    embedder : SentenceTransformer
        Loaded multilingual-e5-large model.
    isic_emb : dict[str, torch.Tensor]
        Precomputed ISIC division embeddings.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Fetch projects in priority order
    cur.execute(
        """
        SELECT id, title, repository_id, type
        FROM projects
        ORDER BY
            CASE type
                WHEN 'QDA_PROJECT' THEN 0
                WHEN 'QD_PROJECT' THEN 1
                WHEN 'OTHER_PROJECT' THEN 2
                ELSE 3
            END,
            CASE repository_id
                WHEN 1 THEN 0
                WHEN 5 THEN 1
                ELSE 2
            END,
            id
        """
    )
    projects = cur.fetchall()

    print(f"\nClassifying {len(projects)} projects (QDA_PROJECT first)...")
    print("=" * 80)

    start_time = time.time()
    classified = 0

    # Process each project
    for idx, (project_id, title, repo_id, ptype) in enumerate(projects, 1):
        repo_label = "Zenodo" if repo_id == 1 else ("DANS" if repo_id == 5 else f"Repo {repo_id}")
        ptype_label = ptype or "UNKNOWN"

        print(f"\n[{idx}/{len(projects)}] {repo_label} | {ptype_label} | Project {project_id}")
        print(f"    Title: {title[:80]}")

        text, has_qda = build_project_text(cur, project_id, downloads_folder)

        if not text or len(text.strip()) < MIN_TEXT_LENGTH:
            print("    Insufficient text, skipping")
            continue

        print("    Ranking by embedding similarity...")
        primary, prim_name, secondary, sec_name, top_k = get_top_isic_by_similarity(
            text,
            embedder,
            isic_emb,
            isic_list,
            TOP_K_CANDIDATES,
        )

        sim_score = top_k[0]["similarity"] if top_k else 0.0

        print("    Top 3 candidates:")
        for i, cand in enumerate(top_k[:3], 1):
            print(f"      {i}. {cand['code']}: {cand['similarity']:.4f}")

        # Update project classification
        cur.execute(
            """
            UPDATE projects
            SET primary_class = ?,
                secondary_class = ?,
                similarity_score = ?,
                has_qda_files = ?,
                classified_at = datetime('now')
            WHERE id = ?
            """,
            (primary, secondary, sim_score, 1 if has_qda else 0, project_id),
        )
        conn.commit()

        print(f"    Assigned primary class: {primary}")
        classified += 1

        print("    Classifying primary files...")
        classify_primary_files(
            cur,
            conn,
            project_id,
            downloads_folder,
            isic_list,
            embedder,
            isic_emb,
        )

    conn.close()

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print("Classification complete.")
    print(f"  Classified projects: {classified}")
    if classified > 0:
        print(f"  Time: {elapsed:.1f}s ({elapsed/classified:.2f}s per project)")
    else:
        print(f"  Time: {elapsed:.1f}s (no projects classified)")
    print("=" * 80)

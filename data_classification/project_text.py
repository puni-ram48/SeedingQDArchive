"""
Project text construction utilities for the ISIC Rev.5 classification pipeline.

This module builds unified project-level text blocks by combining:
- Metadata (title, description)
- Extracted content from primary qualitative data files
- Extracted content from QDA containers (REFI-QDA, NVivo, ATLAS.ti, etc.)

The resulting text block is used to generate semantic embeddings for
project-level ISIC classification. QDA files are prioritized because
they typically contain richer qualitative content.
"""

import os
import sqlite3

from extractor import extract_text_from_file
from config import MIN_TEXT_LENGTH, QDA_EXTS, PRIMARY_EXTS

# ---------------------------------------------------------------------------
# Check for QDA Files
# ---------------------------------------------------------------------------
def check_has_qda_files(cur, project_id: int) -> bool:
    """
    Returns True if the project contains at least one QDA software file.

    Parameters
    ----------
    cur : sqlite3.Cursor
        Database cursor.
    project_id : int
        Project identifier.

    Returns
    -------
    bool
        True if QDA file exists, False otherwise.
    """
    cur.execute(
        """
        SELECT COUNT(*)
        FROM files
        WHERE project_id = ?
          AND status = 'SUCCEEDED'
          AND file_type IN ({})
        """.format(",".join(f"'{ext}'" for ext in QDA_EXTS)),
        (project_id,),
    )
    return cur.fetchone()[0] > 0

# ---------------------------------------------------------------------------
# Build Project-Level Text Block
# ---------------------------------------------------------------------------
def build_project_text(cur, project_id: int, downloads_folder: str) -> tuple:
    """
    Builds a unified text block for a project by combining:
    - Title
    - Description
    - Extracted content previews from primary files and QDA containers

    Parameters
    ----------
    cur : sqlite3.Cursor
        Database cursor.
    project_id : int
        Project identifier.
    downloads_folder : str
        Root folder where downloaded files are stored.

    Returns
    -------
    tuple[str, bool]
        (text_block, has_qda_files)
    """
    # Fetch metadata
    cur.execute(
        """
        SELECT title, description,
               download_repository_folder,
               download_project_folder
        FROM projects
        WHERE id = ?
        """,
        (project_id,),
    )
    row = cur.fetchone()
    if not row:
        return ("", False)

    title, description, repo_folder, proj_folder = row

    # Check QDA priority
    has_qda = check_has_qda_files(cur, project_id)

    # Fetch all successfully downloaded files
    cur.execute(
        """
        SELECT file_name, file_type, status
        FROM files
        WHERE project_id = ? AND status = 'SUCCEEDED'
        """,
        (project_id,),
    )
    file_rows = cur.fetchall()

    extracted_texts = []

    # Extract content from each file
    for file_name, file_type, status in file_rows:
        ext = (file_type or "").lower()

        full_path = os.path.join(
            downloads_folder,
            repo_folder,
            proj_folder,
            file_name,
        )

        if not os.path.exists(full_path):
            continue

        text = extract_text_from_file(full_path)

        if not text or len(text.strip()) < MIN_TEXT_LENGTH:
            continue

        # Skip large structured files (CSV, Excel)
        if ext in {"csv", "tsv", "xlsx", "xls", "ods"}:
            continue

        extracted_texts.append(text[:2000])

    # Build final text block
    parts = []

    if title:
        parts.append(f"PROJECT TITLE:\n{title}\n")

    if description:
        parts.append(f"PROJECT DESCRIPTION:\n{description}\n")

    if extracted_texts:
        parts.append("CONTENT PREVIEW:\n" + "\n\n".join(extracted_texts))

    text_block = "\n".join(parts)

    return (text_block, has_qda)

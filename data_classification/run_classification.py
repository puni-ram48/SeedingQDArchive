"""
Entry point for running the ISIC Rev.5 semantic classification pipeline.

This script orchestrates the full workflow:
1. Load configuration paths
2. Load ISIC Rev.5 division metadata
3. Initialize multilingual-e5-large embedder
4. Precompute ISIC division embeddings
5. Ensure database schema contains required classification columns
6. Execute project-level and file-level classification with QDA prioritization

The pipeline is designed to operate on large qualitative research archives
and produce consistent, interpretable ISIC Rev.5 division assignments.
"""

import os
import sys

from config import (
    DB_FILE,
    DOWNLOAD_FOLDER,
    ISIC_JSON_PATH,
)
from isic import load_isic_divisions, precompute_isic_embeddings
from embedder import load_embedder
from classifier import init_database_schema, run_isic_classification

def main():
    """Main execution entry point for the ISIC classification pipeline."""

    print("\n" + "=" * 80)
    print("ISIC Rev.5 Classification - Step 2 (QDA Priority, multilingual-e5-large, chunking)")
    print("=" * 80)

    db_path = DB_FILE
    downloads_folder = DOWNLOAD_FOLDER

    # Validate paths
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    if not os.path.exists(downloads_folder):
        print(f"Downloads folder not found: {downloads_folder}")
        sys.exit(1)

    # Load ISIC taxonomy
    print("\nLoading ISIC Rev.5 divisions...")
    isic_list = load_isic_divisions(ISIC_JSON_PATH)

    # Load embedding model
    embedder = load_embedder()

    # Precompute ISIC embeddings
    isic_emb = precompute_isic_embeddings(embedder, isic_list)

    # Ensure DB schema is ready
    print("\nInitializing database schema...")
    init_database_schema(db_path)

    # Run classification
    print("\nRunning classification (QDA files prioritized)...")
    run_isic_classification(db_path, downloads_folder, isic_list, embedder, isic_emb)

    print("\nDone.")
    print("=" * 80)

if __name__ == "__main__":
    main()

"""
pipeline.py

Unified pipeline for Zenodo and DANS with DOI-based progress tracking.

Usage:
  python pipeline.py              ← Run both Zenodo and DANS (resumes from where it stopped)
  python pipeline.py --zenodo     ← Run Zenodo only
  python pipeline.py --dans       ← Run DANS only
  python pipeline.py --status     ← Show current status
"""

import sys
import os
import gc
import time
from datetime import datetime

from config import (
    DB_FILE, DOWNLOAD_FOLDER,
    QUERIES_EXTENSIONS, QUERIES_TOOLS, QUERIES_HIGH_PRECISION,
    QUERIES_GERMAN, QUERIES_DUTCH, QUERIES_NORWEGIAN,
    QUERIES_SPANISH, QUERIES_FRENCH, QUERIES_PORTUGUESE,
    ZENODO_QUERIES, DANS_QUERIES
)
from database import setup_database, get_connection
from zenodo import search_zenodo
from dans import run_dans_pipeline


def load_processed_dois(conn):
    """Load all DOIs already in database for duplicate checking."""
    cursor = conn.cursor()
    cursor.execute("SELECT doi FROM projects WHERE doi IS NOT NULL")
    dois = set(row[0] for row in cursor.fetchall())
    print(f"  Loaded {len(dois)} already-processed DOIs from database")
    return dois


def get_completed_queries(conn, repo_id):
    """Get list of queries that have at least one project in database."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT query_string FROM projects WHERE repository_id = ? AND query_string IS NOT NULL",
        (repo_id,)
    )
    completed = set(row[0] for row in cursor.fetchall())
    return completed


def show_status(conn):
    """Show current pipeline status."""
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("PIPELINE STATUS")
    print("="*70)
    
    # Zenodo status
    print("\n ZENODO (Repository ID: 1)")
    cursor.execute("SELECT COUNT(*) FROM projects WHERE repository_id = 1")
    total = cursor.fetchone()[0]
    print(f"   Projects: {total}")
    
    completed_queries = get_completed_queries(conn, 1)
    print(f"   Queries with data: {len(completed_queries)}/{len(ZENODO_QUERIES)}")
    
    # DANS status
    print("\n DANS (Repository ID: 5)")
    cursor.execute("SELECT COUNT(*) FROM projects WHERE repository_id = 5")
    total = cursor.fetchone()[0]
    print(f"   Projects: {total}")
    
    if total > 0:
        completed_queries = get_completed_queries(conn, 5)
        print(f"   Queries with data: {len(completed_queries)}/{len(DANS_QUERIES)}")
    else:
        print(f"   Status: NOT STARTED")

    # File statistics
    print("\n FILE STATISTICS")
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN status = 'SUCCEEDED' THEN 1 ELSE 0 END) as succeeded,
            SUM(CASE WHEN status = 'FAILED_TOO_LARGE' THEN 1 ELSE 0 END) as too_large,
            SUM(CASE WHEN status = 'FAILED_LOGIN_REQUIRED' THEN 1 ELSE 0 END) as login_required,
            SUM(CASE WHEN status = 'FAILED_SERVER_UNRESPONSIVE' THEN 1 ELSE 0 END) as server_error,
            COUNT(*) as total
        FROM files
    """)
    result = cursor.fetchone()
    succeeded = result[0] or 0
    too_large = result[1] or 0
    login_required = result[2] or 0
    server_error = result[3] or 0
    total_files = result[4] or 0
    
    print(f"   SUCCEEDED:                    {succeeded}")
    print(f"   FAILED_TOO_LARGE:             {too_large}")
    print(f"   FAILED_LOGIN_REQUIRED:        {login_required}")
    print(f"   FAILED_SERVER_UNRESPONSIVE:   {server_error}")
    print(f"   Total files:                  {total_files}")
    
    print("\n" + "="*70)


def run_zenodo_pipeline(conn, processed_dois):
    """
    Run Zenodo pipeline with all queries.
    Skips already processed DOIs automatically.
    """
    print("\n" + "="*70)
    print("ZENODO PIPELINE (Repository ID: 1)")
    print("="*70)
    
    os.makedirs(os.path.join(DOWNLOAD_FOLDER, "zenodo"), exist_ok=True)
    
    # Track progress
    total_queries = len(ZENODO_QUERIES)
    completed_queries = 0
    
    for i, query in enumerate(ZENODO_QUERIES, 1):
        print(f"\n{'─'*70}")
        print(f"Query {i}/{total_queries}: {query}")
        print(f"{'─'*70}")
        
        try:
            search_zenodo(conn, query, processed_dois)
            completed_queries += 1
        except Exception as e:
            print(f"  ERROR in query '{query}': {e}")
            print(f"  Continuing with next query...")
        
        # Force garbage collection after each query
        gc.collect()
        time.sleep(5)
        
        # Show progress
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM projects WHERE repository_id = 1")
        total_projects = cursor.fetchone()[0]
        print(f"\n  Progress: {total_projects} projects collected so far")
    
    print(f"\n  Zenodo pipeline complete. Processed {completed_queries}/{total_queries} queries.")


def run_dans_pipeline_with_resume(conn, processed_dois):
    """
    Run DANS pipeline with all queries across all stations.
    Skips already processed DOIs automatically.
    """
    print("\n" + "="*70)
    print("DANS PIPELINE (Repository ID: 5)")
    print("="*70)
    
    # Import here to avoid circular imports
    from dans import run_dans_pipeline as dans_pipeline
    
    try:
        dans_pipeline(conn, DANS_QUERIES, processed_dois)
    except Exception as e:
        print(f"  ERROR in DANS pipeline: {e}")
        print(f"  Continuing...")
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM projects WHERE repository_id = 5")
    total_projects = cursor.fetchone()[0]
    print(f"\n  DANS pipeline complete. Total projects: {total_projects}")


def main():
    args = sys.argv[1:]
    
    # Status only
    if "--status" in args:
        conn = get_connection()
        show_status(conn)
        conn.close()
        return
    
    print("="*70)
    print("QDArchive Unified Pipeline")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Setup
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    conn = setup_database()
    
    # Load already processed DOIs (for resuming)
    processed_dois = load_processed_dois(conn)
    
    # Show current status before starting
    show_status(conn)
    
    # Determine what to run
    run_zenodo = "--dans" not in args  # Run Zenodo unless --dans only
    run_dans = "--zenodo" not in args   # Run DANS unless --zenodo only
    
    # Handle explicit flags
    if "--zenodo" in args and "--dans" not in args:
        run_zenodo = True
        run_dans = False
    elif "--dans" in args and "--zenodo" not in args:
        run_zenodo = False
        run_dans = True
    
    # Run pipelines
    if run_zenodo:
        run_zenodo_pipeline(conn, processed_dois)
    
    if run_dans:
        run_dans_pipeline_with_resume(conn, processed_dois)
    
    # Final status
    print("\n" + "="*70)
    print("FINAL STATUS")
    print("="*70)
    show_status(conn)
    
    conn.close()
    
    print("\n" + "="*70)
    print("DONE!")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Database: {DB_FILE}")
    print(f"  Downloads: {DOWNLOAD_FOLDER}/")
    print("="*70)


if __name__ == "__main__":
    main()

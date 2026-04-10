"""
pipeline.py

Usage:
  python pipeline.py                    ← run all repos
  python pipeline.py --zenodo           ← Continue Zenodo (German, Spanish, French, Portuguese)
  python pipeline.py --dans             ← Run DANS only
"""

import sys
import os
import gc
import time
from datetime import datetime

from config import (
    DB_FILE, DOWNLOAD_FOLDER,
    QUERIES_EXTENSIONS, QUERIES_TOOLS,
    QUERIES_ENGLISH, QUERIES_GERMAN, QUERIES_DUTCH,
    QUERIES_NORWEGIAN, QUERIES_SPANISH, QUERIES_FRENCH, QUERIES_PORTUGUESE,
    DANS_QUERIES
)
from database import setup_database, print_summary, get_connection 
from zenodo import search_zenodo
from dans import run_dans_pipeline

def get_completed_queries(conn, repo_id):
    """Get list of queries already completed for a repository"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT query_string FROM projects WHERE repository_id = ?",
        (repo_id,)
    )
    completed = set(row[0] for row in cursor.fetchall() if row[0])
    return completed

def load_processed_ids(conn):
    """Load all DOIs already in database"""
    cursor = conn.cursor()
    cursor.execute("SELECT doi FROM projects WHERE doi IS NOT NULL")
    ids = set(row[0] for row in cursor.fetchall())
    print(f"  Loaded {len(ids)} already-processed DOIs from DB")
    return ids

def show_status(conn):
    """Show current pipeline status"""
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("PIPELINE STATUS")
    print("="*70)
    
    # Zenodo status
    print("\n ZENODO (Repository ID: 1)")
    cursor.execute("SELECT COUNT(*) FROM projects WHERE repository_id = 1")
    total = cursor.fetchone()[0]
    print(f"   Projects: {total}")
    
    completed_zenodo = get_completed_queries(conn, 1)
    print(f"   Queries completed: {len(completed_zenodo)}")
    
    # Show which query groups are done
    all_zenodo_queries = {
        "Extensions (*.qdpx, *.nvp, etc)": QUERIES_EXTENSIONS,
        "Tools (NVivo, ATLAS.ti, etc)": QUERIES_TOOLS,
        "English": QUERIES_ENGLISH,
        "German": QUERIES_GERMAN,
        "Spanish": QUERIES_SPANISH,
        "French": QUERIES_FRENCH,
        "Portuguese": QUERIES_PORTUGUESE,
    }
    
    print("\n   Query group coverage:")
    for group_name, queries in all_zenodo_queries.items():
        completed_count = sum(1 for q in queries if q in completed_zenodo)
        total_count = len(queries)
        pct = (completed_count / total_count * 100) if total_count > 0 else 0
        status = "✓" if completed_count == total_count else "⋯"
        print(f"   {status} {group_name}: {completed_count}/{total_count} ({pct:.0f}%)")
    
    # DANS status
    print("\n DANS (Repository ID: 5)")
    cursor.execute("SELECT COUNT(*) FROM projects WHERE repository_id = 5")
    total = cursor.fetchone()[0]
    print(f"   Projects: {total}")
    
    if total > 0:
        completed_dans = get_completed_queries(conn, 5)
        print(f"   Queries completed: {len(completed_dans)}/{len(DANS_QUERIES)}")
    else:
        print(f"   Status: NOT STARTED")

    # File statistics - UPDATED for TEXT status values
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

def run_zenodo_batch(conn, queries, batch_name):
    """Run a batch of Zenodo queries"""
    print("\n" + "="*70)
    print(f"ZENODO BATCH: {batch_name}")
    print("="*70)
    
    os.makedirs(os.path.join(DOWNLOAD_FOLDER, "zenodo"), exist_ok=True)
    
    completed = get_completed_queries(conn, 1)
    remaining = [q for q in queries if q not in completed]
    
    if not remaining:
        print(f"✓ All queries in this batch already completed!")
        return
    
    print(f"\nQueries to process: {len(remaining)}/{len(queries)}")
    print(f"Already completed: {len(completed)}")
    
    processed_dois = load_processed_ids(conn)
    
    for i, query in enumerate(remaining, 1):
        print(f"\n{'─'*70}")
        print(f"Query {i}/{len(remaining)}: {query}")
        print(f"{'─'*70}")
        
        search_zenodo(conn, query, processed_dois)
        
        # Force garbage collection after each query
        gc.collect()
        time.sleep(5)  # Pause between queries
        
        # Show progress every 5 queries
        if i % 5 == 0:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM projects WHERE repository_id = 1")
            total = cursor.fetchone()[0]
            print(f"\n   Progress: {total} total Zenodo projects in database")
    
    print(f"\n✓ Batch '{batch_name}' complete!")

def main():
    args = sys.argv[1:]
    
    if "--status" in args:
        conn = get_connection()
        show_status(conn)
        conn.close()
        return
    
    print("="*70)
    print("QDArchive Optimized Pipeline")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Setup
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    conn = setup_database()
    
    # Show current status first
    show_status(conn)
    
    if "--zenodo-extensions" in args:
        # Highest priority: file extensions (100% hit rate for QDA files)
        run_zenodo_batch(conn, QUERIES_EXTENSIONS, "File Extensions")
        
    elif "--zenodo-tools" in args:
        # Tool names
        run_zenodo_batch(conn, QUERIES_TOOLS, "Tool Names")
        
    elif "--zenodo-german" in args:
        run_zenodo_batch(conn, QUERIES_GERMAN, "German Queries")
        
    elif "--zenodo-spanish" in args:
        run_zenodo_batch(conn, QUERIES_SPANISH, "Spanish Queries")
        
    elif "--zenodo-french" in args:
        run_zenodo_batch(conn, QUERIES_FRENCH, "French Queries")
        
    elif "--zenodo-portuguese" in args:
        run_zenodo_batch(conn, QUERIES_PORTUGUESE, "Portuguese Queries")
        
    elif "--zenodo" in args:
        # Run remaining Zenodo queries in order of priority
        print("\nRunning remaining Zenodo queries...")
        
        batches = [
            ("Extensions", QUERIES_EXTENSIONS),
            ("Tools", QUERIES_TOOLS),
            ("German", QUERIES_GERMAN),
            ("Spanish", QUERIES_SPANISH),
            ("French", QUERIES_FRENCH),
            ("Portuguese", QUERIES_PORTUGUESE),
        ]
        
        for batch_name, queries in batches:
            run_zenodo_batch(conn, queries, batch_name)
            gc.collect()  # Clean memory between batches
    
    elif "--dans" in args:
        print("\nRunning DANS pipeline...")
        processed_dois = load_processed_ids(conn)
        run_dans_pipeline(conn, DANS_QUERIES, processed_dois)
        
    else:
        print("\nUsage:")
        print("  python pipeline.py --zenodo-extensions   ← Run extension queries (highest priority)")
        print("  python pipeline.py --zenodo-german       ← Run German queries")
        print("  python pipeline.py --zenodo              ← Run all remaining Zenodo")
        print("  python pipeline.py --dans                ← Run DANS")
        conn.close()
        return
    
    # Final reports
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
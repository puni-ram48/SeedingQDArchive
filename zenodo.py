"""
zenodo.py 
Zenodo repository scraper (Repository ID: 1)
API: https://zenodo.org/api/records 
"""

import os
import time
from datetime import datetime

from config import (
    REPOSITORIES, DOWNLOAD_FOLDER,
    ZENODO_PAGE_SIZE, ZENODO_MAX_PAGES,
    SLEEP_BETWEEN_PAGES, SLEEP_BETWEEN_QUERIES,
    TARGET_EXTENSIONS, SUPPORTING_EXTENSIONS,
    ZENODO_TOKEN,
)
from database import save_project, project_exists
from utils import (
    safe_filename, strip_html, is_qda_file, is_supporting_file,
    has_qualitative_hints, should_skip_project_type,
    download_file, fetch_with_retry, detect_language,
    build_file_records, print_download_result
)

# Repository config
REPO        = REPOSITORIES["zenodo"]
REPO_ID     = REPO["id"]
REPO_URL    = REPO["url"]
REPO_API    = REPO["api"]
REPO_FOLDER = REPO["folder"]

def get_headers():
    headers = {"Accept": "application/json"}
    if ZENODO_TOKEN:
        headers["Authorization"] = f"Bearer {ZENODO_TOKEN}"
    return headers

def extract_zenodo_metadata(record):
    """Extract all metadata fields from a Zenodo API record"""
    metadata  = record.get("metadata", {})
    record_id = str(record.get("id", ""))

    title       = metadata.get("title", "Unknown")
    description = strip_html(metadata.get("description", ""))

    # DOI — prefer concept DOI (always points to latest version)
    concept_doi = record.get("conceptdoi", "")
    version_doi = record.get("doi", "") or metadata.get("doi", "")
    if concept_doi:
        doi = f"https://doi.org/{concept_doi}"
    elif version_doi:
        doi = f"https://doi.org/{version_doi}"
    else:
        doi = ""

    version     = metadata.get("version", "")
    upload_date = metadata.get("publication_date", "")
    lang_raw    = metadata.get("language", "") or detect_language(description, title)

    # Keywords — stored 
    keywords_raw = metadata.get("keywords", [])
    keywords     = keywords_raw if isinstance(keywords_raw, list) else []

    # Persons — creators as AUTHOR
    creators = metadata.get("creators", [])
    persons  = [
        {"name": c.get("name", ""), "role": "AUTHOR"}
        for c in creators if c.get("name")
    ]

    # License
    license_raw = metadata.get("license", {})
    license_str = license_raw.get("id", "") if isinstance(license_raw, dict) else str(license_raw or "")
    licenses    = [license_str] if license_str else []

    # Resource type
    resource_type = metadata.get("resource_type", {}).get("type", "dataset")

    return {
        "record_id":     record_id,
        "title":         title,
        "description":   description,
        "doi":           doi,
        "version":       version,
        "upload_date":   upload_date,
        "language":      lang_raw,
        "keywords":      keywords,
        "persons":       persons,
        "licenses":      licenses,
        "resource_type": resource_type,
        "project_url":   f"{REPO_URL}/records/{record_id}",
    }
    
def process_record(conn, record, query_string, processed_dois):
    """
    Process one Zenodo record following the professor's algorithm:
    1. If QDA file found → download everything
    2. If skip type → skip
    3. Else if qualitative hints → download supporting files
    4. Else → skip

    Fix: folder only created when a file actually downloads successfully
    """
    files = record.get("files", [])
    if not files:
        return

    meta      = extract_zenodo_metadata(record)
    record_id = meta["record_id"]
    doi       = meta["doi"] or record_id

    if doi in processed_dois:
        return

    existing_id = project_exists(conn, doi, REPO_ID)
    if existing_id:
        processed_dois.add(doi)
        return

    # Classify files
    qda_files = [f for f in files if is_qda_file(f.get("key", ""))]
    has_qda   = len(qda_files) > 0

    if not has_qda:
        if should_skip_project_type(meta["resource_type"]):
            return

        hint_text = f"{meta['title']} {meta['description']} " + " ".join(meta["keywords"])
        if not has_qualitative_hints(hint_text):
            return

        files_to_download = [
            f for f in files if is_supporting_file(f.get("key", ""))
        ]
        if not files_to_download:
            return

        print(f"\n  Qualitative Dataset (no QDA): {meta['title']}")
    else:
        files_to_download = files
        print(f"\n QDA Dataset: {meta['title']}")
        print(f"License:     {meta['licenses']}")
        print(f"QDA files:   {[f['key'] for f in qda_files]}")
        print(f"All files:   {len(files)}")

        # Build path — DO NOT create folder yet
    # Folder only created when a file actually downloads successfully
    project_folder = record_id
    dataset_path   = os.path.join(DOWNLOAD_FOLDER, REPO_FOLDER, project_folder)

    # Download files and track results
    download_complete = True
    any_downloaded    = False
    file_results = []  # NEW: Track each file's result

    for file_info in files_to_download:
        filename = file_info.get("key", "")
        file_url = file_info.get("links", {}).get("self", "")
        file_size = file_info.get("size", 0)  # NEW: Get size from Zenodo
        
        if not filename or not file_url:
            continue

        safe_name = safe_filename(filename)
        filepath  = os.path.join(dataset_path, safe_name)

        # create_dir=True means folder is only created when content is saved
        result = download_file(
            file_url, filepath,
            headers=get_headers(),
            create_dir=True
        )
        print_download_result(filename, result)

        # NEW: Track result for database
        file_results.append({
            "filename": filename,
            "size": file_size,
            "download_result": result
        })

        if result == "downloaded":
            any_downloaded = True
        elif result.startswith("failed"):
            download_complete = False

    # Skip saving to DB if nothing was downloaded and no QDA metadata to keep
    if not any_downloaded and not has_qda:
        return

    # Build file records for ALL files
    all_filenames = [f.get("key", "") for f in files]
    file_records = build_file_records(file_results)

    # Save to database
    project_data = {
        "query_string":                 query_string,
        "repository_id":                REPO_ID,
        "repository_url":               REPO_URL,
        "project_url":                  meta["project_url"],
        "version":                      meta["version"],
        "title":                        meta["title"],
        "description":                  meta["description"],
        "language":                     meta["language"],
        "doi":                          doi,
        "upload_date":                  meta["upload_date"],
        "download_date":                datetime.now().isoformat(),
        "download_repository_folder":   REPO_FOLDER,
        "download_project_folder":      project_folder,
        "download_version_folder":      meta["version"] or None,
        "download_method":              "API-CALL",
        "has_qda_file":                 1 if has_qda else 0,
        "download_complete":            1 if download_complete else 0,
        "files":                        file_records,
        "keywords":                     meta["keywords"],
        "persons":                      meta["persons"],
        "licenses":                     meta["licenses"],
    }

    save_project(conn, project_data)
    processed_dois.add(doi)  
    time.sleep(0.5)

def search_zenodo(conn, query, processed_dois):
    """Search Zenodo for a query and process all results"""
    print(f"\n{'='*60}")
    print(f"[Zenodo] Searching for '{query}'...")
    print(f"{'='*60}")

    page          = 1
    total_checked = 0
    new_found     = 0

    while page <= ZENODO_MAX_PAGES:
        params = {
            "q":            query,
            "type":         "dataset",
            "size":         ZENODO_PAGE_SIZE,
            "page":         page,
            "sort":         "bestmatch",
            "all_versions": "false",
        }

        response = fetch_with_retry(REPO_API, params=params, headers=get_headers())
        if response is None:
            break

        data    = response.json()
        records = data.get("hits", {}).get("hits", [])
        total   = data.get("hits", {}).get("total", 0)

        if not records:
            print(f"  No more results after page {page}")
            break

        total_pages = min(ZENODO_MAX_PAGES, (total // ZENODO_PAGE_SIZE) + 1)
        print(f"  Page {page}/{total_pages}: {len(records)} records (total: {total})")

        if page == 1 and total > 10000:
            print(f"  ⚠️  {total} results — Zenodo limit is 10,000. "
                  f"Use narrower queries for full coverage.")

        before = len(processed_dois)
        for record in records:
            process_record(conn, record, query, processed_dois)
        new_found     += len(processed_dois) - before
        total_checked += len(records)

        if len(records) < ZENODO_PAGE_SIZE:
            break

        page += 1
        time.sleep(SLEEP_BETWEEN_PAGES)

    print(f"\n  Finished '{query}' on Zenodo")
    print(f" Pages scanned:  {page}")
    print(f" Records checked: {total_checked}")
    print(f" New projects:  {new_found}")

def run_zenodo_pipeline(conn, queries, processed_dois):
    """Run full Zenodo pipeline with all queries"""
    print("\n" + "="*60)
    print("ZENODO PIPELINE (Repository ID: 1)")
    print("="*60)

    os.makedirs(os.path.join(DOWNLOAD_FOLDER, REPO_FOLDER), exist_ok=True)

    for query in queries:
        search_zenodo(conn, query, processed_dois)
        time.sleep(SLEEP_BETWEEN_QUERIES)

    print(f"\n Zenodo pipeline complete")
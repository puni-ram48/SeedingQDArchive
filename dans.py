"""
dans.py 
DANS SSH Data Station scraper (Repository ID: 5)
API: https://ssh.datastations.nl (Dataverse API)
"""

import os
import time
from datetime import datetime

from config import (
    REPOSITORIES, DOWNLOAD_FOLDER,
    DANS_PAGE_SIZE, SLEEP_BETWEEN_PAGES, SLEEP_BETWEEN_QUERIES,
    TARGET_EXTENSIONS, SUPPORTING_EXTENSIONS,
    DANS_TOKEN,
)
from database import save_project, project_exists
from utils import (
    safe_filename, strip_html, is_qda_file, is_supporting_file,
    has_qualitative_hints, should_skip_project_type,
    download_file, fetch_with_retry, detect_language,
    build_file_records, print_download_result
)

# Repository config
REPO        = REPOSITORIES["dans"]
REPO_ID     = REPO["id"]
REPO_URL    = REPO["url"]
REPO_FOLDER = REPO["folder"]
STATIONS    = REPO["stations"]

# Max consecutive 403 errors before skipping rest of dataset
MAX_CONSECUTIVE_403 = 2

# Headers
def get_headers():
    headers = {"Accept": "application/json"}
    if DANS_TOKEN:
        headers["X-Dataverse-key"] = DANS_TOKEN
    return headers

def extract_dans_persons(dataset):
    """Extract persons from DANS Dataverse citation metadata"""
    persons = []
    try:
        fields = (dataset.get("latestVersion", {})
                         .get("metadataBlocks", {})
                         .get("citation", {})
                         .get("fields", []))
        for field in fields:
            if field.get("typeName") == "author":
                for entry in field.get("value", []):
                    name = entry.get("authorName", {}).get("value", "")
                    if name:
                        persons.append({"name": name, "role": "AUTHOR"})
            elif field.get("typeName") == "datasetContact":
                for entry in field.get("value", []):
                    name = entry.get("datasetContactName", {}).get("value", "")
                    if name:
                        persons.append({"name": name, "role": "UPLOADER"})
    except:
        pass
    return persons

def extract_dans_keywords(dataset):
    """Extract keywords from DANS Dataverse metadata — stored as-is per meeting notes"""
    keywords = []
    try:
        fields = (dataset.get("latestVersion", {})
                         .get("metadataBlocks", {})
                         .get("citation", {})
                         .get("fields", []))
        for field in fields:
            if field.get("typeName") == "keyword":
                for entry in field.get("value", []):
                    kw = entry.get("keywordValue", {}).get("value", "")
                    if kw:
                        keywords.append(kw)
    except:
        pass
    return keywords

def extract_dans_language(dataset, title="", description=""):
    """Extract language from DANS metadata"""
    try:
        fields = (dataset.get("latestVersion", {})
                         .get("metadataBlocks", {})
                         .get("citation", {})
                         .get("fields", []))
        for field in fields:
            if field.get("typeName") == "language":
                for entry in field.get("value", []):
                    lang = entry if isinstance(entry, str) else entry.get("value", "")
                    if lang:
                        return lang
    except:
        pass
    return detect_language(description, title)

def process_dans_dataset(conn, item, query_string, processed_dois,
                         station_api, station_folder, station_name):
    """
    Process one DANS dataset following the professor's algorithm:
    1. If QDA file found → download everything
    2. If skip type → skip
    3. Else if qualitative hints → download supporting files
    4. Else → skip

    Fixes:
    - No empty folders: folder only created when a file actually downloads
    - Skip after 2 consecutive 403 errors: avoids wasting time on
      restricted collections like SMGI oral history
    """
    title = item.get("name", "Unknown")
    global_id = item.get("global_id", "")
    if not global_id:
        return

    if global_id in processed_dois:
        return

    existing_id = project_exists(conn, global_id, REPO_ID)
    if existing_id:
        processed_dois.add(global_id)
        return

    try:
        # Get full dataset details
        response = fetch_with_retry(
            f"{station_api}/api/datasets/:persistentId",
            params={"persistentId": global_id},
            headers=get_headers()
        )
        if response is None:
            return

        dataset = response.json().get("data", {})
        files = dataset.get("latestVersion", {}).get("files", [])
        if not files:
            return

        # Get file list
        file_list = [f.get("dataFile", {}).get("filename", "") for f in files]

        # Classify files
        qda_filenames = [fn for fn in file_list if is_qda_file(fn)]
        has_qda = len(qda_filenames) > 0

        # Extract metadata
        description_raw = item.get("description", "")
        description = strip_html(description_raw)
        persons = extract_dans_persons(dataset)
        keywords = extract_dans_keywords(dataset)
        language = extract_dans_language(dataset, title, description)

        # License
        license_raw = (dataset.get("latestVersion", {})
                              .get("license", {})
                              .get("name", ""))
        licenses = [license_raw] if license_raw else []

        # DOI
        doi = f"https://doi.org/{global_id.replace('doi:', '')}" if "doi:" in global_id else global_id

        # Version
        version_number = str(dataset.get("latestVersion", {}).get("versionNumber", ""))
        version_minor  = str(dataset.get("latestVersion", {}).get("versionMinorNumber", ""))
        version = f"{version_number}.{version_minor}" if version_number else ""

        # Upload date
        release_time = dataset.get("latestVersion", {}).get("releaseTime", "")
        upload_date = release_time[:10] if release_time else ""

        # Project URL
        project_url = item.get("url", f"https://doi.org/{global_id}")

        # Project folder — use dataset ID from global_id
        dataset_id     = global_id.split(":")[-1].replace("/", "-")
        project_folder = dataset_id

        if not has_qda:
            hint_text = f"{title} {description} " + " ".join(keywords)
            if not has_qualitative_hints(hint_text):
                return

            files_to_download = [
                f for f in files
                if is_supporting_file(f.get("dataFile", {}).get("filename", ""))
            ]
            if not files_to_download:
                return

            print(f"\n  Qualitative Dataset (no QDA): {title}")
        else:
            files_to_download = files
            print(f"\n  DANS QDA Dataset: {title}")
            print(f"     QDA files:   {qda_filenames}")
            print(f"     All files:   {len(files)}")

        # Build dataset path — but DO NOT create folder yet
        # Folder will only be created when a file actually downloads successfully
        dataset_path = os.path.join(
            DOWNLOAD_FOLDER, REPO_FOLDER, station_folder, project_folder
        )

                # Download files 
        download_complete    = True
        consecutive_failures = 0
        any_downloaded       = False
        file_results = []  # NEW: Track each file's result

        for file_info in files_to_download:
            filename = file_info.get("dataFile", {}).get("filename", "")
            file_id  = file_info.get("dataFile", {}).get("id")
            file_size = file_info.get("dataFile", {}).get("filesize", 0)  # NEW: Get size from DANS
            
            if not filename or not file_id:
                continue

            safe_name    = safe_filename(filename)
            download_url = f"{station_api}/api/access/datafile/{file_id}"
            filepath     = os.path.join(dataset_path, safe_name)

            # download_file creates directory only when content is actually saved
            result = download_file(
                download_url, filepath,
                headers=get_headers(),
                create_dir=True   # ← creates folder only on successful download
            )

            print_download_result(filename, result)

            # NEW: Track for database
            file_results.append({
                "filename": filename,
                "size": file_size,
                "download_result": result
            })

            if result == "downloaded":
                any_downloaded = True
                consecutive_failures = 0  # reset on success

            elif "403" in result:
                consecutive_failures += 1
                download_complete = False

                # Skip rest of dataset after consecutive 403s
                # This handles restricted collections like SMGI oral history
                if consecutive_failures >= MAX_CONSECUTIVE_403:
                    print(f"  {consecutive_failures} consecutive 403 errors"
                          f" — collection appears fully restricted")
                    print(f"  Skipping remaining files in this dataset")
                    download_complete = False
                    break

            elif result.startswith("failed"):
                download_complete = False
                consecutive_failures = 0

        # Only save to database if:
        # 1. Files were successfully downloaded, OR
        # 2. Dataset has QDA file records worth keeping in metadata
        if not any_downloaded and not has_qda:
            # Nothing downloaded and no QDA files — skip saving to DB too
            return

        # Build file records for ALL files (metadata only — not just downloaded)
                # NEW: Build file records with metadata (including skipped reasons)
        file_records = build_file_records(file_results)

        # Save to database
        project_data = {
            "query_string":                 query_string,
            "repository_id":                REPO_ID,
            "repository_url":               REPO_URL,
            "project_url":                  project_url,
            "version":                      version,
            "title":                        title,
            "description":                  description,
            "language":                     language,
            "doi":                          doi,
            "upload_date":                  upload_date,
            "download_date":                datetime.now().isoformat(),
            "download_repository_folder":   f"{REPO_FOLDER}/{station_folder}",
            "download_project_folder":      project_folder,
            "download_version_folder":      version or None,
            "download_method":              "API-CALL",
            "has_qda_file":                 1 if has_qda else 0,
            "download_complete":            1 if download_complete else 0,
            "files":                        file_records,
            "keywords":                     keywords,
            "persons":                      persons,
            "licenses":                     licenses,
        }

        save_project(conn, project_data)
        processed_dois.add(global_id)
        time.sleep(0.5)
            

    except Exception as e:
        print(f" Error processing DANS dataset '{title}': {e}")


def search_dans(conn, query, processed_dois, station_api, station_folder, station_name):
    """Search a specific DANS data station for a query"""
    print(f"\n{'='*60}")
    print(f"[{station_name}] Searching for '{query}'...")
    print(f"{'='*60}")

    page          = 0
    total_checked = 0
    new_found     = 0

    while True:
        params = {
            "q":        query,
            "type":     "dataset",
            "start":    page * DANS_PAGE_SIZE,
            "per_page": DANS_PAGE_SIZE,
        }

        response = fetch_with_retry(
            f"{station_api}/api/search",
            params=params,
            headers=get_headers()
        )
        if response is None:
            break

        data  = response.json()
        items = data.get("data", {}).get("items", [])
        total = data.get("data", {}).get("total_count", 0)

        if not items:
            print(f"  No more results after page {page}")
            break

        print(f"  Page {page+1}: {len(items)} datasets (total: {total})")
        total_checked += len(items)

        before = len(processed_dois)
        for item in items:
            process_dans_dataset(
                conn, item, query, processed_dois,
                station_api, station_folder, station_name
            )
        new_found += len(processed_dois) - before

        if len(items) < DANS_PAGE_SIZE:
            break

        page += 1
        time.sleep(SLEEP_BETWEEN_PAGES)

    print(f"\n  Finished '{query}' on {station_name}")
    print(f"     Records checked:  {total_checked}")
    print(f"     New projects:     {new_found}")

def run_dans_pipeline(conn, queries, processed_dois):
    """
    Run full DANS pipeline across ALL 5 data stations.
    All stations use identical Dataverse API — just different URLs.

    Stations by priority for QDA files:
    1. SSH (Social Sciences & Humanities) — most relevant
    2. Archaeology — some qualitative fieldwork
    3. DataverseNL — mixed institutional data
    4. Life Sciences — unlikely but possible
    5. Physical & Technical Sciences — unlikely for QDA
    """
    print("\n" + "="*60)
    print("DANS PIPELINE (Repository ID: 5)")
    print("Searching all 5 DANS Data Stations")
    print("="*60)

    # Sort stations by priority
    sorted_stations = sorted(
        STATIONS.items(),
        key=lambda x: x[1]["priority"]
    )

    for station_key, station in sorted_stations:
        station_api    = station["api"]
        station_folder = station["folder"]
        station_name   = station["name"]

        print(f"\n{'─'*60}")
        print(f"Station: {station_name}")
        print(f"URL:     {station_api}")
        print(f"{'─'*60}")

        for query in queries:
            search_dans(
                conn, query, processed_dois,
                station_api, station_folder, station_name
            )
            time.sleep(SLEEP_BETWEEN_QUERIES)

    print(f"\n All DANS stations complete")
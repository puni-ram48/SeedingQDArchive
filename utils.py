"""
utils.py 
Shared helper functions used by all repository modules
"""

import os
import re
import time
import requests
from config import (
    TARGET_EXTENSIONS, SUPPORTING_EXTENSIONS,
    SKIP_PROJECT_TYPES, QUALITATIVE_HINTS, MAX_RETRIES,
    MAX_FILE_SIZE_MB  
)

# Folder/filename helpers
def safe_folder_name(text, max_len=60):
    """Convert text to safe folder name"""
    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in str(text))
    return safe.strip()[:max_len]


def safe_filename(filename, max_len=150):
    """Truncate long filenames to avoid Windows path limit issues"""
    if len(filename) <= max_len:
        return filename
    name, ext = os.path.splitext(filename)
    return name[:max_len - len(ext)] + ext

def strip_html(text, max_len=2000):
    """Remove HTML tags from text"""
    clean = re.sub('<[^<]+?>', '', text or '')
    return clean.strip()[:max_len]

# File type helpers
def get_file_extension(filename):
    """Get lowercase file extension"""
    return os.path.splitext(filename)[1].lower()

def is_qda_file(filename):
    """Check if file is a QDA file"""
    return get_file_extension(filename) in TARGET_EXTENSIONS

def is_supporting_file(filename):
    """Check if file is a supporting document"""
    return get_file_extension(filename) in SUPPORTING_EXTENSIONS

def should_skip_project_type(project_type):
    """Check if project type should be skipped"""
    return str(project_type).lower() in SKIP_PROJECT_TYPES

def has_qualitative_hints(text):
    """Check if text contains qualitative research hints"""
    if not text:
        return False
    text_lower = text.lower()
    return any(hint.lower() in text_lower for hint in QUALITATIVE_HINTS)

def download_file(url, filepath, headers=None, create_dir=False):
    """
    Download a file from URL to filepath.
    Skips files larger than MAX_FILE_SIZE_MB.

    create_dir=False (default):
        Does NOT create directory automatically.
        Folder is only created when actual content is saved.
        This prevents empty folders when all downloads fail.

    create_dir=True:
        Creates directory before downloading.
        Use only when you are sure the download will succeed.

    Returns: 'downloaded', 'skipped', 'too large (SIZE)', or 'failed (reason)'
    """
    if os.path.exists(filepath):
        return "skipped"

    try:
        response = requests.get(
            url,
            headers=headers or {},
            timeout=60,
            stream=True
        )

        if response.status_code == 200:
            # Check Content-Length header BEFORE downloading
            content_length = response.headers.get('content-length')
            if content_length:
                try:
                    file_size_bytes = int(content_length)
                    file_size_mb = file_size_bytes / (1024 * 1024)
                    
                    if file_size_mb > MAX_FILE_SIZE_MB:
                        response.close()
                        return f"too large ({file_size_mb:.1f}MB)"
                except ValueError:
                    pass
            
            # Now download the content
            content = response.content
            
            if len(content) > 100:
                # Double-check actual size after download
                file_size_mb = len(content) / (1024 * 1024)
                if file_size_mb > MAX_FILE_SIZE_MB:
                    return f"too large ({file_size_mb:.1f}MB)"
                
                # Create directory and save
                dir_path = os.path.dirname(filepath)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                with open(filepath, "wb") as f:
                    f.write(content)
                return "downloaded"
            else:
                return "failed (empty file)"

        elif response.status_code == 403:
            return "failed (403 — access restricted)"
        elif response.status_code == 401:
            return "failed (401 — authentication required)"
        elif response.status_code == 404:
            return "failed (404 — not found)"
        else:
            return f"failed ({response.status_code})"

    except requests.exceptions.Timeout:
        return "failed (timeout)"
    except requests.exceptions.ConnectionError as e:
        return f"failed (connection error)"
    except Exception as e:
        return f"failed ({e})"


# API fetch with retry
def fetch_with_retry(url, params=None, headers=None, max_retries=MAX_RETRIES):
    """
    Fetch URL with automatic retry on server errors.
    Returns response object or None.
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                params=params or {},
                headers=headers or {"Accept": "application/json"},
                timeout=30
            )

            if response.status_code == 200:
                return response

            elif response.status_code in [502, 503]:
                wait = 30 * (attempt + 1)
                print(f"  Server error {response.status_code} "
                      f"— waiting {wait}s (retry {attempt+1}/{max_retries})")
                time.sleep(wait)

            elif response.status_code == 429:
                print(f"  Rate limited — waiting 60s")
                time.sleep(60)

            elif response.status_code == 401:
                print(f"  Authentication required (401)")
                return None

            elif response.status_code == 403:
                print(f"  Access forbidden (403)")
                return None

            else:
                print(f"  API error {response.status_code}: {response.text[:150]}")
                return None

        except requests.exceptions.ConnectionError:
            wait = 15 * (attempt + 1)
            print(f"  Connection error — waiting {wait}s (retry {attempt+1})")
            time.sleep(wait)

        except Exception as e:
            print(f"  Unexpected error: {e}")
            return None

    print(f"  Failed after {max_retries} retries")
    return None

def detect_language(text, title=""):
    """
    Simple language detection based on common words.
    Returns BCP 47 language code or empty string if unknown.
    """
    if not text and not title:
        return ""

    combined = f"{title} {text}".lower()

    language_markers = {
        "de": ["und", "der", "die", "das", "ist", "ein", "eine", "mit", "von", "für",
               "interview", "forschung", "qualitativ", "transkript"],
        "nl": ["de", "het", "een", "van", "en", "in", "dat", "zijn", "voor", "met",
               "kwalitatief", "onderzoek", "interview"],
        "fr": ["le", "la", "les", "de", "du", "des", "et", "en", "un", "une",
               "recherche", "qualitative", "entretien"],
        "es": ["el", "la", "los", "las", "de", "del", "en", "un", "una", "con",
               "investigación", "cualitativa", "entrevista"],
        "pt": ["de", "da", "do", "em", "um", "uma", "que", "para", "com", "não",
               "pesquisa", "qualitativa", "entrevista"],
        "no": ["og", "i", "er", "en", "et", "av", "til", "som", "med", "på",
               "kvalitativ", "forskning", "intervju"],
        "it": ["di", "il", "la", "le", "un", "una", "e", "in", "del", "che",
               "qualitativa", "intervista", "ricerca"],
    }

    scores = {}
    words = combined.split()
    for lang, markers in language_markers.items():
        score = sum(1 for w in words if w in markers)
        if score > 0:
            scores[lang] = score

    if not scores:
        return "en"

    best_lang = max(scores, key=scores.get)
    if scores[best_lang] < 2:
        return "en"

    return best_lang

def build_file_records(files_data):
    """
    Build list of file records for FILES table.
    
    files_data: list of dicts with 'filename'/'key' and optional 'size' and 'download_result'
    
    Returns: list of file records with name, type, size, status, skip_reason
    """
    records = []
    
    for file_info in files_data:
        # Handle different API response formats
        if isinstance(file_info, dict):
            filename = file_info.get("filename") or file_info.get("key", "")
            file_size = file_info.get("size", 0)
            download_result = file_info.get("download_result", "")
        else:
            filename = file_info
            file_size = 0
            download_result = ""
        
        if not filename:
            continue
        
        ext = get_file_extension(filename)
        
        # Determine status and skip reason
        status = 0  # default: not downloaded
        skip_reason = None
        
        if download_result == "downloaded":
            status = 1  # downloaded
        elif "too large" in download_result:
            status = 3  # too large
            skip_reason = download_result  # e.g., "too large (125.5MB)"
        elif download_result == "skipped":
            status = 2  # skipped
        elif download_result.startswith("failed"):
            status = 2  # skipped
            skip_reason = download_result
        
        records.append({
            "file_name": filename,
            "file_type": ext.lstrip(".") if ext else "unknown",
            "file_size": file_size,
            "status": status,
            "skip_reason": skip_reason
        })
    
    return records

def print_download_result(filename, result):
    """Print formatted download result"""
    if result == "downloaded":
        print(f"     {filename}")
    elif result == "skipped":
        print(f"     {filename} (exists)")
    elif "restricted" in result or "authentication" in result:
        print(f"     {filename} — {result}")
    else:
        print(f"     {filename} — {result}")
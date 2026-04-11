"""
utils.py
Shared helper functions for repository modules including file handling,
API requests, language detection, and qualitative data classification.
"""

import os
import re
import time
from typing import List, Dict, Tuple, Optional, Any
import requests

from config import (
    TARGET_EXTENSIONS,
    SUPPORTING_EXTENSIONS,
    SKIP_PROJECT_TYPES,
    QUALITATIVE_HINTS,
    MAX_RETRIES,
    MAX_FILE_SIZE_MB,
)


# ============================================================================
# FILE AND FOLDER NAME HELPERS
# ============================================================================

def safe_folder_name(text: str, max_len: int = 60) -> str:
    """
    Convert arbitrary text to a safe folder name by replacing unsafe characters.

    Args:
        text: Input text to sanitize
        max_len: Maximum length of the resulting folder name

    Returns:
        Sanitized folder name safe for filesystem usage
    """
    safe = "".join(c if c.isalnum() or c in "-_ " else "_" for c in str(text))
    return safe.strip()[:max_len]


def safe_filename(filename: str, max_len: int = 150) -> str:
    """
    Truncate long filenames to avoid Windows path length limitations.

    Args:
        filename: Original filename
        max_len: Maximum allowed length

    Returns:
        Truncated filename with extension preserved
    """
    if len(filename) <= max_len:
        return filename
    name, ext = os.path.splitext(filename)
    return name[: max_len - len(ext)] + ext


def strip_html(text: str, max_len: int = 2000) -> str:
    """
    Remove HTML tags from text and truncate to reasonable length.

    Args:
        text: HTML or plain text content
        max_len: Maximum length after cleaning

    Returns:
        Cleaned plain text
    """
    clean = re.sub(r"<[^<]+?>", "", text or "")
    return clean.strip()[:max_len]


# ============================================================================
# FILE TYPE CLASSIFICATION
# ============================================================================

def get_file_extension(filename: str) -> str:
    """
    Extract lowercase file extension from filename.

    Args:
        filename: Name of the file

    Returns:
        Lowercase file extension including the dot (e.g., '.pdf')
    """
    return os.path.splitext(filename)[1].lower()


def is_qda_file(filename: str) -> bool:
    """
    Check if file is a qualitative data analysis (QDA) project file.

    Args:
        filename: Name of the file to check

    Returns:
        True if file extension matches known QDA formats
    """
    return get_file_extension(filename) in TARGET_EXTENSIONS


def is_supporting_file(filename: str) -> bool:
    """
    Check if file is a supporting document (text, PDF, spreadsheet, etc.).

    Args:
        filename: Name of the file to check

    Returns:
        True if file extension matches supporting document formats
    """
    return get_file_extension(filename) in SUPPORTING_EXTENSIONS


def should_skip_project_type(project_type: str) -> bool:
    """
    Determine if a project type should be skipped (e.g., publications, software).

    Args:
        project_type: Type identifier from repository metadata

    Returns:
        True if the project type should be excluded
    """
    return str(project_type).lower() in SKIP_PROJECT_TYPES


def has_qualitative_hints(text: str) -> bool:
    """
    Check if text contains qualitative research keywords.

    Args:
        text: Text to analyze (title, description, keywords)

    Returns:
        True if qualitative research indicators are found
    """
    if not text:
        return False
    text_lower = text.lower()
    return any(hint.lower() in text_lower for hint in QUALITATIVE_HINTS)


# ============================================================================
# QUALITATIVE DATA CLASSIFIER
# ============================================================================

def should_download_dataset(
    project_title: str, project_description: str, files_metadata: List[Dict[str, str]]
) -> Tuple[bool, str, int]:
    """
    Determine if a dataset contains actual qualitative data worthy of download.

    This function analyzes file names, extensions, and metadata to score the
    likelihood that a dataset contains genuine qualitative research data
    (interview transcripts, QDA files, coding schemes, etc.) rather than
    methodological papers, quantitative data, or software artifacts.

    The scoring system:
    - Score >= 40: Download (strong qualitative evidence)
    - Score >= 20 with transcripts or keywords: Download (possible qualitative)
    - Score < 20: Skip (insufficient evidence)

    Args:
        project_title: Title of the research project
        project_description: Description from repository metadata
        files_metadata: List of dicts with 'filename' keys

    Returns:
        Tuple containing:
        - should_download: Boolean decision
        - reason: Human-readable explanation
        - score: Numerical score (0-100+)
    """
    score = 0
    reasons: List[str] = []
    warnings: List[str] = []

    # Extract file information
    file_names = [f.get("filename", f.get("key", "")).lower() for f in files_metadata]
    file_extensions = [f.split(".")[-1] if "." in f else "" for f in file_names]

    # ------------------------------------------------------------------------
    # STRONG POSITIVE SIGNALS - High confidence qualitative indicators
    # ------------------------------------------------------------------------

    # QDA file patterns - 100% confidence, immediate download
    qda_patterns = [
        "qdpx",
        "qdc",
        "nvp",
        "nvpx",
        "mx24",
        "mx22",
        "mx20",
        "mqda",
        "ppj",
        "pprj",
        "qlt",
        "f4p",
        "qpd",
        "hpr7",
        "atlasproj",
    ]
    qda_files = [f for f in file_names if any(p in f for p in qda_patterns)]
    if qda_files:
        return True, f"QDA project files present ({len(qda_files)} file(s))", 100

    # Interview transcript patterns
    transcript_patterns = [
        "transcript",
        "interview",
        "participant",
        "informant",
        "verbatim",
        "focus group",
        "oral history",
        "narrative",
    ]
    transcript_files = [
        f for f in file_names if any(p in f for p in transcript_patterns)
    ]
    if transcript_files:
        score += min(50, len(transcript_files) * 15)
        reasons.append(f"{len(transcript_files)} transcript/interview file(s)")

    # Multiple text/document files (qualitative data pattern)
    text_extensions = ["txt", "rtf", "doc", "docx", "odt", "pdf"]
    text_files = [f for f in file_names if f.split(".")[-1] in text_extensions]
    if len(text_files) >= 5:
        score += 25
        reasons.append(f"{len(text_files)} text/document files")
    elif len(text_files) >= 3:
        score += 15
        reasons.append(f"{len(text_files)} text/document files")

    # ------------------------------------------------------------------------
    # WEAK POSITIVE SIGNALS - Supporting evidence
    # ------------------------------------------------------------------------

    # Qualitative keywords in title/description
    text_to_check = f"{project_title} {project_description}".lower()
    qualitative_keywords = [
        "interview",
        "transcript",
        "qualitative",
        "thematic",
        "phenomenolog",
        "ethnograph",
        "grounded theory",
        "focus group",
        "narrative",
        "discourse",
        "coding",
        "codebook",
        "caqdas",
        "semi-structured",
        "open-ended",
    ]
    keyword_matches = sum(1 for kw in qualitative_keywords if kw in text_to_check)
    if keyword_matches >= 3:
        score += 20
        reasons.append(f"{keyword_matches} qualitative keyword(s) in metadata")
    elif keyword_matches >= 1:
        score += 10
        reasons.append(f"{keyword_matches} qualitative keyword(s) in metadata")

    # ------------------------------------------------------------------------
    # NEGATIVE SIGNALS - Penalties for non-qualitative content
    # ------------------------------------------------------------------------

    # Only PDF files - likely publication, not data
    if file_extensions and all(ext == "pdf" for ext in file_extensions):
        score -= 60
        warnings.append("Only PDF files detected (likely publication)")

    # Many PDFs without transcripts
    pdf_count = file_extensions.count("pdf")
    if pdf_count >= 3 and not transcript_files:
        score -= 30
        warnings.append(f"{pdf_count} PDF(s) with no transcripts (likely publication)")

    # Code/software files
    code_extensions = ["py", "r", "js", "java", "cpp", "c", "exe", "dll", "so", "jar", "ipynb"]
    code_count = sum(1 for ext in file_extensions if ext in code_extensions)
    if code_count > 0:
        score -= 20
        warnings.append(f"{code_count} code/software file(s) detected")

    # Publication indicators in metadata
    publication_indicators = [
        "paper",
        "article",
        "publication",
        "preprint",
        "supplementary",
        "journal",
        "conference",
        "proceedings",
        "review",
        "literature",
    ]
    if any(ind in text_to_check for ind in publication_indicators):
        if not transcript_files and not qda_files:
            score -= 25
            warnings.append("Publication detected with no data files")

    # ------------------------------------------------------------------------
    # FINAL DECISION
    # ------------------------------------------------------------------------

    # Build reason string
    if warnings:
        reason = "; ".join(warnings)
    elif reasons:
        reason = "; ".join(reasons)
    else:
        reason = "No qualitative indicators found"

    # Apply decision thresholds
    if score >= 40:
        return True, f"Download: {reason}", score
    elif score >= 20 and (transcript_files or keyword_matches >= 2):
        return True, f"Possible qualitative data: {reason}", score
    else:
        return False, f"Skip: {reason}", score


# ============================================================================
# FILE DOWNLOAD UTILITIES
# ============================================================================

def download_file(
    url: str, filepath: str, headers: Optional[Dict] = None, create_dir: bool = False
) -> str:
    """
    Download a file from URL with size checking and retry logic.

    Args:
        url: Source URL for the file
        filepath: Destination path on local filesystem
        headers: Optional HTTP headers (authentication, etc.)
        create_dir: If True, create parent directory before downloading

    Returns:
        Status string: 'downloaded', 'skipped', 'too large (SIZE)', or 'failed (reason)'
    """
    if os.path.exists(filepath):
        return "skipped"

    try:
        response = requests.get(url, headers=headers or {}, timeout=60, stream=True)

        if response.status_code == 200:
            # Check content length before downloading
            content_length = response.headers.get("content-length")
            if content_length:
                try:
                    file_size_bytes = int(content_length)
                    file_size_mb = file_size_bytes / (1024 * 1024)
                    if file_size_mb > MAX_FILE_SIZE_MB:
                        response.close()
                        return f"too large ({file_size_mb:.1f}MB)"
                except ValueError:
                    pass

            # Download content
            content = response.content

            if len(content) > 100:
                # Double-check actual size
                file_size_mb = len(content) / (1024 * 1024)
                if file_size_mb > MAX_FILE_SIZE_MB:
                    return f"too large ({file_size_mb:.1f}MB)"

                # Create directory and save
                dir_path = os.path.dirname(filepath)
                if dir_path and create_dir:
                    os.makedirs(dir_path, exist_ok=True)
                with open(filepath, "wb") as f:
                    f.write(content)
                return "downloaded"
            else:
                return "failed (empty file)"

        elif response.status_code == 403:
            return "failed (403 - access restricted)"
        elif response.status_code == 401:
            return "failed (401 - authentication required)"
        elif response.status_code == 404:
            return "failed (404 - not found)"
        else:
            return f"failed ({response.status_code})"

    except requests.exceptions.Timeout:
        return "failed (timeout)"
    except requests.exceptions.ConnectionError:
        return "failed (connection error)"
    except Exception as e:
        return f"failed ({e})"


def fetch_with_retry(
    url: str,
    params: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    max_retries: int = MAX_RETRIES,
) -> Optional[requests.Response]:
    """
    Fetch URL with automatic retry on server errors and rate limiting.

    Args:
        url: Target URL
        params: Query parameters
        headers: HTTP headers
        max_retries: Maximum number of retry attempts

    Returns:
        Response object on success, None on failure
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                params=params or {},
                headers=headers or {"Accept": "application/json"},
                timeout=30,
            )

            if response.status_code == 200:
                return response

            elif response.status_code in [502, 503]:
                wait = 30 * (attempt + 1)
                print(
                    f"  Server error {response.status_code} - "
                    f"retrying in {wait}s ({attempt + 1}/{max_retries})"
                )
                time.sleep(wait)

            elif response.status_code == 429:
                print(f"  Rate limited - waiting 60 seconds")
                time.sleep(60)

            elif response.status_code in [401, 403]:
                print(f"  Access denied ({response.status_code})")
                return None

            else:
                print(f"  API error {response.status_code}: {response.text[:150]}")
                return None

        except requests.exceptions.ConnectionError:
            wait = 15 * (attempt + 1)
            print(f"  Connection error - retrying in {wait}s ({attempt + 1}/{max_retries})")
            time.sleep(wait)

        except Exception as e:
            print(f"  Unexpected error: {e}")
            return None

    print(f"  Failed after {max_retries} retries")
    return None


# ============================================================================
# LANGUAGE DETECTION
# ============================================================================

def detect_language(text: str, title: str = "") -> str:
    """
    Detect primary language of text using keyword matching.

    Args:
        text: Main text content
        title: Title text (optional)

    Returns:
        BCP 47 language code (e.g., 'en', 'de', 'nl') or empty string if unknown
    """
    if not text and not title:
        return ""

    combined = f"{title} {text}".lower()

    language_markers = {
        "de": [
            "und",
            "der",
            "die",
            "das",
            "ist",
            "ein",
            "eine",
            "mit",
            "von",
            "für",
            "interview",
            "forschung",
            "qualitativ",
            "transkript",
        ],
        "nl": [
            "de",
            "het",
            "een",
            "van",
            "en",
            "in",
            "dat",
            "zijn",
            "voor",
            "met",
            "kwalitatief",
            "onderzoek",
            "interview",
        ],
        "fr": [
            "le",
            "la",
            "les",
            "de",
            "du",
            "des",
            "et",
            "en",
            "un",
            "une",
            "recherche",
            "qualitative",
            "entretien",
        ],
        "es": [
            "el",
            "la",
            "los",
            "las",
            "de",
            "del",
            "en",
            "un",
            "una",
            "con",
            "investigación",
            "cualitativa",
            "entrevista",
        ],
        "pt": [
            "de",
            "da",
            "do",
            "em",
            "um",
            "uma",
            "que",
            "para",
            "com",
            "não",
            "pesquisa",
            "qualitativa",
            "entrevista",
        ],
        "no": [
            "og",
            "i",
            "er",
            "en",
            "et",
            "av",
            "til",
            "som",
            "med",
            "på",
            "kvalitativ",
            "forskning",
            "intervju",
        ],
        "it": [
            "di",
            "il",
            "la",
            "le",
            "un",
            "una",
            "e",
            "in",
            "del",
            "che",
            "qualitativa",
            "intervista",
            "ricerca",
        ],
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


# ============================================================================
# DATABASE RECORD BUILDERS
# ============================================================================

def build_file_records(files_data: List[Dict]) -> List[Dict]:
    """
    Build file records for the FILES table from download results.

    Converts download result strings to schema-compliant status enums:
    - SUCCEEDED: Successfully downloaded
    - FAILED_TOO_LARGE: File exceeded size limit
    - FAILED_LOGIN_REQUIRED: Authentication or permission error
    - FAILED_SERVER_UNRESPONSIVE: Network or server error

    Args:
        files_data: List of dicts with 'filename'/'key' and 'download_result'

    Returns:
        List of file record dicts with 'file_name', 'file_type', and 'status'
    """
    records = []

    for file_info in files_data:
        # Handle different API response formats
        if isinstance(file_info, dict):
            filename = file_info.get("filename") or file_info.get("key", "")
            download_result = file_info.get("download_result", "")
        else:
            filename = file_info
            download_result = ""

        if not filename:
            continue

        ext = get_file_extension(filename)

        # Convert download_result to schema-compliant status
        if download_result == "downloaded":
            status = "SUCCEEDED"
        elif "too large" in download_result.lower():
            status = "FAILED_TOO_LARGE"
        elif "403" in download_result or "401" in download_result or "restricted" in download_result.lower():
            status = "FAILED_LOGIN_REQUIRED"
        elif download_result.startswith("failed") or "connection error" in download_result or "timeout" in download_result:
            status = "FAILED_SERVER_UNRESPONSIVE"
        elif download_result == "skipped":
            status = "SUCCEEDED"
        else:
            status = "FAILED_SERVER_UNRESPONSIVE"

        records.append(
            {
                "file_name": filename,
                "file_type": ext.lstrip(".") if ext else "unknown",
                "status": status,
            }
        )

    return records


def print_download_result(filename: str, result: str) -> None:
    """
    Print formatted download result.

    Args:
        filename: Name of the file being downloaded
        result: Result string from download_file()
    """
    if result == "downloaded":
        print(f"     [OK] {filename}")
    elif result == "skipped":
        print(f"     [SKIP] {filename} (already exists)")
    elif "too large" in result.lower():
        print(f"     [LARGE] {filename} - {result}")
    elif "restricted" in result.lower() or "authentication" in result.lower():
        print(f"     [DENIED] {filename} - {result}")
    else:
        print(f"     [FAIL] {filename} - {result}")

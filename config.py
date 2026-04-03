"""
config.py 
All configuration settings, repository IDs, tokens, and queries
"""

# Database 
DB_FILE         = "qdarchive.db"
DOWNLOAD_FOLDER = "downloads"

#  Repository IDs
REPOSITORIES = {
    "zenodo": {
        "id":   1,
        "name": "Zenodo",
        "url":  "https://zenodo.org",
        "api":  "https://zenodo.org/api/records",
        "folder": "zenodo",
    },
    "dans": {
        "id":   5,
        "name": "DANS",
        "url":  "https://dans.knaw.nl",
        "folder": "dans",
        # All 5 DANS data stations — all use identical Dataverse API
        "stations": {
            "ssh": {
                "name":   "DANS SSH (Social Sciences & Humanities)",
                "api":    "https://ssh.datastations.nl",
                "folder": "ssh",
                "priority": 1,   # Most relevant for QDA
            },
            "archaeology": {
                "name":   "DANS Archaeology",
                "api":    "https://archaeology.datastations.nl",
                "folder": "archaeology",
                "priority": 2,   # Some qualitative fieldwork
            },
            "lifesciences": {
                "name":   "DANS Life Sciences",
                "api":    "https://lifesciences.datastations.nl",
                "folder": "lifesciences",
                "priority": 3,   # Unlikely but possible
            },
            "phys_tech": {
                "name":   "DANS Physical & Technical Sciences",
                "api":    "https://phys-techsciences.datastations.nl",
                "folder": "phys_tech",
                "priority": 4,   # Unlikely for QDA
            },
            "dataversenl": {
                "name":   "DataverseNL",
                "api":    "https://dataverse.nl",
                "folder": "dataversenl",
                "priority": 2,   # Mixed institutional data
            },
        }
    }
}


# API Tokens (optional but recommended) 
# Get Zenodo token: zenodo.org → account → Applications → New token
ZENODO_TOKEN = ""   # paste your token here

# Get DANS token: ssh.datastations.nl → account → API Token
DANS_TOKEN   = ""   # paste your token here

# Pagination settings
ZENODO_PAGE_SIZE        = 25    # Zenodo max for anonymous (100 with token)
ZENODO_MAX_PAGES        = 400   # Hard limit: 400 × 25 = 10,000 results
DANS_PAGE_SIZE          = 1000  # Dataverse supports up to 1000
MAX_RETRIES             = 3
SLEEP_BETWEEN_PAGES     = 2     # seconds
SLEEP_BETWEEN_QUERIES   = 5     # seconds

# FILE SIZE LIMIT: Maximum file size to download (in MB)
# Files larger than this will be skipped
MAX_FILE_SIZE_MB = 100

# ALL known QDA file extensions 
TARGET_EXTENSIONS = [
    # REFI Standard / QDAcity
    ".qdpx", ".qdc",
    # NVivo
    ".nvp", ".nvpx",
    # ATLAS.ti
    ".atlasproj", ".hpr7",
    # MaxQDA — all versions
    ".mqda", ".mqbac", ".mqtc", ".mqex", ".mqmtr",
    ".mx24", ".mx24bac", ".mc24", ".mex24",
    ".mx22", ".mex22",
    ".mx20", ".mx18", ".mx12", ".mx11",
    ".mx5", ".mx4", ".mx3", ".mx2", ".m2k",
    # MaxQDA export/helper files
    ".loa", ".sea", ".mtr", ".mod",
    # QDA Miner
    ".ppj", ".pprj", ".qlt",
    # f4analyse
    ".f4p",
    # Quirkos
    ".qpd",
]

# Supporting file extensions (download if qualitative hints found) 
SUPPORTING_EXTENSIONS = [
    ".txt", ".pdf", ".rtf", ".docx", ".doc",
    ".csv", ".tsv", ".xlsx", ".xls", ".ods",
]

# Project types to skip (no QDA files expected)
SKIP_PROJECT_TYPES = {
    "publication", "presentation", "poster", "lesson",
    "software", "workflow", "image", "video", "event", "model"
}

# Qualitative research hint keywords 
QUALITATIVE_HINTS = [
    # English
    "interview", "transcript", "qualitative", "coding", "thematic",
    "grounded theory", "ethnograph", "focus group", "narrative",
    "phenomenolog", "codebook", "caqdas", "semi-structured",
    "open-ended", "biographical", "life history", "action research",
    "interpretive", "discourse analysis", "content analysis",
    # German
    "interview", "transkript", "qualitativ", "kodierung", "leitfaden",
    "gruppendiskussion", "biografie",
    # Dutch
    "kwalitatief", "transcriptie", "focusgroep", "diepte-interview",
    # Norwegian
    "kvalitativ", "intervju", "fokusgruppe",
    # French
    "qualitatif", "entretien", "transcription", "groupe de discussion",
    # Spanish
    "cualitativa", "entrevista", "transcripción", "grupo focal",
    # Portuguese
    "qualitativa", "entrevista", "transcrição", "grupo focal",
    # Italian
    "qualitativa", "intervista", "trascrizione",
]


# SEARCH QUERIES

# Pass 1 — QDA file extension queries (most targeted, 100% hit rate)
QUERIES_EXTENSIONS = [
    "*.qdpx", "*.qdc",
    "*.nvp", "*.nvpx",
    "*.hpr7", "*.atlasproj",
    "*.mqda", "*.mx24", "*.mx22", "*.mx20",
    "*.mx18", "*.mx12", "*.mex24", "*.mex22",
    "*.ppj", "*.pprj", "*.qlt",
    "*.f4p", "*.qpd",
]

# Pass 2 — QDA tool name queries
QUERIES_TOOLS = [
    "qdpx", "REFI-QDA",
    "NVivo", "ATLAS.ti", "MaxQDA",
    "Dedoose", "QDAcity", "QDA Miner",
    "Transana", "f4analyse", "CAQDAS",
]

# Pass 3 — Qualitative research method queries (English)
QUERIES_ENGLISH = [
    "interview transcript",
    "qualitative research",
    "qualitative data",
    "focus group",
    "ethnography",
    "grounded theory",
    "semi-structured interview",
    "thematic analysis",
    "narrative analysis",
    "case study research",
    "participant observation",
]

# Pass 4 — German queries (Zenodo, DANS)
QUERIES_GERMAN = [
    "qualitative Forschung",
    "qualitatives Interview",
    "Leitfadeninterview",
    "Gruppendiskussion",
    "Biografieforschung",
    "qualitative Inhaltsanalyse",
    "Transkript Interview",
]

# Pass 5 — Dutch queries (DANS)
QUERIES_DUTCH = [
    "kwalitatief onderzoek",
    "kwalitatief interview",
    "focusgroep",
    "diepte-interview",
    "transcriptie interview",
]

# Pass 6 — Norwegian queries (DANS)
QUERIES_NORWEGIAN = [
    "kvalitativ forskning",
    "kvalitativt intervju",
    "fokusgruppe",
    "dybdeintervju",
]

# Pass 7 — Spanish queries (Zenodo)
QUERIES_SPANISH = [
    "investigación cualitativa",
    "entrevista cualitativa",
    "grupo focal",
    "análisis temático",
    "transcripción entrevista",
]

# Pass 8 — French queries (Zenodo)
QUERIES_FRENCH = [
    "recherche qualitative",
    "entretien qualitatif",
    "groupe de discussion",
    "analyse thématique",
]

# Pass 9 — Portuguese queries (Zenodo)
QUERIES_PORTUGUESE = [
    "pesquisa qualitativa",
    "entrevista qualitativa",
    "grupo focal",
    "análise temática",
]

# Combined query list for Zenodo (all passes)
ZENODO_QUERIES = (
    QUERIES_EXTENSIONS +
    QUERIES_TOOLS +
    QUERIES_ENGLISH +
    QUERIES_GERMAN +
    QUERIES_SPANISH +
    QUERIES_FRENCH +
    QUERIES_PORTUGUESE
)

# Combined query list for DANS (all passes including Dutch/Norwegian)
DANS_QUERIES = (
    QUERIES_EXTENSIONS +
    QUERIES_TOOLS +
    QUERIES_ENGLISH +
    QUERIES_GERMAN +
    QUERIES_DUTCH +
    QUERIES_NORWEGIAN
)

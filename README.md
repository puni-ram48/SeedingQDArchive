# 📘 SeedingQDArchive: Automated Pipeline for Harvesting Qualitative Research Datasets  

## 1. Introduction  
QDArchive is an automated data‑acquisition pipeline designed to identify, retrieve, and archive **qualitative research datasets** from two major open repositories: **Zenodo** and the **DANS Data Stations** (Dataverse). The system focuses on detecting **QDA project files** (e.g., NVivo, ATLAS.ti, MaxQDA, REFI‑QDA) and **qualitative textual materials** (e.g., interviews, transcripts, field notes) across multiple languages.  

The pipeline adheres to a structured **five‑table data model**, enabling reproducible research, metadata standardization, and downstream analysis.

---

## 2. System Overview  
The pipeline is composed of modular components:

- **Configuration Layer (`config.py`)**  
  Defines repository endpoints, API tokens, pagination rules, file‑type lists, and multilingual search queries.

- **Utility Layer (`utils.py`)**  
  Provides shared functionality for safe file handling, qualitative keyword detection, file downloading with size limits, retry logic, and language identification.

- **Database Layer (`database.py`)**  
  Implements a normalized SQLite schema (PROJECTS, FILES, KEYWORDS, PERSON_ROLE, LICENSES) following the professor’s Data Acquisition Output Format.

- **Repository Harvesters**  
  - **Zenodo (`zenodo.py`)**: Queries Zenodo’s REST API, extracts metadata, and downloads files based on QDA relevance.  
  - **DANS (`dans.py`)**: Searches all five DANS Data Stations, processes Dataverse metadata, and handles restricted collections gracefully.

- **Pipeline Orchestrator (`pipeline.py`)**  
  Coordinates query execution, tracks progress, manages deduplication, and produces final CSV exports.

---

## 3. Data Acquisition Logic  
Each dataset is evaluated using a consistent decision framework:

1. **Presence of QDA files → Download all files**  
2. **Irrelevant project type → Skip**  
3. **Qualitative indicators in metadata → Download supporting files**  
4. **Otherwise → Exclude dataset**

This ensures that the archive prioritizes substantive qualitative research materials.

---

## 4. Output Structure  
All harvested datasets are stored in:

- A structured **download directory** organized by repository and dataset ID.  
- A **SQLite database (`qdarchive.db`)** containing:
  - Project‑level metadata  
  - File‑level metadata and download status  
  - Extracted keywords  
  - Associated persons and roles  
  - License information  

CSV exports are generated automatically for interoperability.

---

## 5. Running the Pipeline  
### Zenodo  
```bash
python pipeline.py --zenodo-extensions
python pipeline.py --zenodo-tools
python pipeline.py --zenodo
```

### DANS  
```bash
python pipeline.py --dans
```

### Status  
```bash
python pipeline.py --status
```

---

## 6. Documentation  
A comprehensive description of the architecture, metadata model, and repository‑specific logic is available in the project’s `/docs` directory.

---

# 📚 7. Data Sources & Citation  
QDArchive harvests publicly available research datasets from two major open‑science infrastructures:

### **Zenodo (CERN, OpenAIRE)**
Zenodo is a general‑purpose open research repository operated by CERN and supported by the European Commission.  
Datasets are retrieved via the **Zenodo REST API**:  
https://zenodo.org/api/records  

When using or redistributing datasets obtained through this pipeline, please cite Zenodo as:  
> Zenodo (CERN). *Zenodo Research Data Repository*. Available at: https://zenodo.org

### **DANS Data Stations (KNAW, Dutch Research Council)**
DANS (Data Archiving and Networked Services) hosts multiple domain‑specific Dataverse installations for long‑term preservation of research data.  
Datasets are retrieved via the **Dataverse API** of the DANS Data Stations:  
https://dans.knaw.nl  

Recommended citation:  
> DANS. *DANS Data Stations (Dataverse)*. Available at: https://dans.knaw.nl

---

## **Dataset‑Level Citations**
Every dataset harvested by QDArchive includes its own DOI and license information.  
Users must cite **each dataset individually**, following the citation format provided by the repository.  

The pipeline preserves:
- DOI (concept DOI or version DOI)  
- Authors / creators  
- Uploaders / dataset contacts  
- License identifiers  
- Keywords  
- Version information  

This ensures that downstream researchers can properly attribute all materials.

---

## **Ethical & Legal Considerations**
- Only **publicly accessible datasets** are harvested.  
- Restricted datasets (e.g., requiring login or permission) are **skipped automatically**.  
- All downloaded files retain their original licenses (e.g., CC‑BY, CC0, custom terms).  
- Users are responsible for complying with dataset‑specific licenses and citation requirements.

---

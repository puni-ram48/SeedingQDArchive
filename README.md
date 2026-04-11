# 📘 **SeedingQDArchive: Automated Pipeline for Harvesting Qualitative Research Datasets**

---

## 🌍 **1. Introduction**
QDArchive is an automated data‑acquisition pipeline designed to identify, retrieve, and archive **qualitative research datasets** from two major open repositories:  
- 🧭 **Zenodo**  
- 🧭 **DANS Data Stations (Dataverse)**  

It focuses on detecting:
- 🗂️ **QDA project files** (NVivo, ATLAS.ti, MaxQDA, REFI‑QDA)  
- 📝 **Qualitative textual materials** (interviews, transcripts, field notes)  
- 🌐 Across multiple languages  

The pipeline adheres to a structured **five‑table data model**, enabling reproducible research, metadata standardization, and downstream analysis.

---

## ⚙️ **2. System Overview**

The pipeline is composed of modular components:

### 🔧 **Configuration Layer (`config.py`)**
Defines repository endpoints, API tokens, pagination rules, file‑type lists, and multilingual search queries.

### 🧩 **Utility Layer (`utils.py`)**
Provides shared functionality for:
- Safe file handling  
- Qualitative keyword detection  
- File downloading with size limits  
- Retry logic  
- Language identification  

### 🗃️ **Database Layer (`database.py`)**
Implements a normalized SQLite schema:
- `PROJECTS`, `FILES`, `KEYWORDS`, `PERSON_ROLE`, `LICENSES`  
Following the professor’s **Data Acquisition Output Format**.

### 🌐 **Repository Harvesters**
- **Zenodo (`zenodo.py`)** → Queries Zenodo’s REST API, extracts metadata, downloads files based on QDA relevance.  
- **DANS (`dans.py`)** → Searches all five DANS Data Stations, processes Dataverse metadata, handles restricted collections gracefully.

### 🚀 **Pipeline Orchestrator (`pipeline.py`)**
Coordinates query execution, tracks progress, manages deduplication, and produces final CSV exports.

---

## 🧠 **3. Data Acquisition Logic**

Each dataset is evaluated using a consistent decision framework:

1. ✅ **Presence of QDA files → Download all files**  
2. 🚫 **Irrelevant project type → Skip**  
3. 🕵️ **Qualitative indicators in metadata → Download supporting files**  
4. ❌ **Otherwise → Exclude dataset**

This ensures the archive prioritizes substantive qualitative research materials.

---

## 📂 **4. Output Structure**

All harvested datasets are stored in:

- 📁 **Structured download directory** organized by repository and dataset ID  
- 🗄️ **SQLite database (`23173040-seeding.db`)** containing:
  - Project‑level metadata  
  - File‑level metadata and download status  
  - Extracted keywords  
  - Associated persons and roles  
  - License information  

---

## 🖥️ **5. Running the Pipeline**

### 🧭 Zenodo
```bash
python pipeline.py --zenodo
```

### 🧭 DANS
```bash
python pipeline.py --dans
```

## 🗃️ **6. Data Sources & Citation**

QDArchive harvests publicly available research datasets from two major open‑science infrastructures:

### 🧩 **Zenodo (CERN, OpenAIRE)**
Zenodo is a general‑purpose open research repository operated by CERN and supported by the European Commission.  
Datasets are retrieved via the **Zenodo REST API**:  
🔗 https://zenodo.org/api/records  

**Citation:**
> Zenodo (CERN). *Zenodo Research Data Repository*. Available at: https://zenodo.org

---

### 🧩 **DANS Data Stations (KNAW, Dutch Research Council)**
DANS hosts multiple domain‑specific Dataverse installations for long‑term preservation of research data.  
Datasets are retrieved via the **Dataverse API**:  
🔗 https://dans.knaw.nl  

**Citation:**
> DANS. *DANS Data Stations (Dataverse)*. Available at: https://dans.knaw.nl

---

## 🧾 **Dataset‑Level Citations**

Every dataset harvested by QDArchive includes its own DOI and license information.  
Users must cite **each dataset individually**, following the repository’s citation format.

The pipeline preserves:
- 🔖 DOI (concept or version)  
- 👩‍💻 Authors / creators  
- 📬 Uploaders / dataset contacts  
- ⚖️ License identifiers  
- 🏷️ Keywords  
- 🔢 Version information  

This ensures proper attribution and reproducibility.

---

## ⚖️ **Ethical & Legal Considerations**

- ✅ Only **publicly accessible datasets** are harvested  
- 🚫 Restricted datasets (login or permission required) are **skipped automatically**  
- 📜 All downloaded files retain their original licenses (CC‑BY, CC0, custom terms)  
- 🧠 Users must comply with dataset‑specific licenses and citation requirements
---

## 🙏 **Acknowledgments**
I would like to express my sincere gratitude to **Prof. Dr. Dirk Riehle, M.B.A.** for providing me with the opportunity to work on this project and for his continuous guidance throughout its development. His insights, feedback, and support were invaluable in shaping the direction and quality of this work.

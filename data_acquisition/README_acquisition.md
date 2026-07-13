# 📘 Part 1: Data Acquisition Pipeline  
*A multilingual, modular scraper for harvesting qualitative research datasets from Zenodo and DANS.*

---

## 📄 Overview
The **Data Acquisition Pipeline** automatically discovers, filters, and downloads qualitative research datasets from:

- **Zenodo** (CERN / OpenAIRE)  
- **DANS Data Stations** (SSH, Archaeology, Life Sciences, Physical & Technical Sciences, DataverseNL)

It identifies:

- QDA project files (NVivo, ATLAS.ti, MaxQDA, REFI‑QDA, QDA Miner)  
- Qualitative textual materials (interviews, transcripts, focus groups, field notes)  
- Multilingual datasets (EN, DE, NL, NO, ES, FR, PT)

All harvested datasets are stored in a structured folder hierarchy and indexed in a **5‑table SQLite database**.

---

## ✨ Features
- Automated harvesting from **two major repositories**  
- Multilingual search queries  
- Smart qualitative detection (QDA files + keyword hints)  
- Strict file‑type filtering  
- Graceful handling of restricted datasets  
- Clean metadata extraction (authors, keywords, licenses, language)  
- Fully normalized SQLite database  
- Modular, reproducible architecture  

---

## 🧱 Folder Structure
```
data_acquisition/
│
├── README_acquisition.md      ← Documentation for Part 1
├── config.py                  ← Central configuration
├── utils.py                   ← Shared utility functions
├── zenodo.py                  ← Zenodo harvester
├── dans.py                    ← DANS harvester (all 5 stations)
├── database.py                ← SQLite schema + insert logic
├── pipeline.py                ← Orchestrator
└── downloads/                 ← All harvested datasets
```

---

## 🧠 How It Works

### **1. Query repositories**
Multilingual search queries target:
- QDA file extensions  
- QDA tool names  
- Transcript patterns  
- Qualitative keywords  

### **2. Evaluate each dataset**
The pipeline checks:
- Does it contain QDA files?  
- Does metadata contain qualitative hints?  
- Is the project type relevant?  
- Are files accessible?  

### **3. Download relevant files**
- If QDA files exist → download **all files**  
- If only qualitative hints exist → download **supporting files**  
- Otherwise → skip  

### **4. Store metadata**
All metadata is saved into:
- `projects`  
- `files`  
- `keywords`  
- `person_role`  
- `licenses`  

### **5. Organize files**
Downloaded files are stored under:
```
downloads/zenodo/<project_id>/
downloads/dans/<station>/<project_id>/
```

---

## 📦 Installation
Clone the repository:

```bash
git clone https://github.com/puni-ram48/SeedingQDArchive.git
cd SeedingQDArchive/data_acquisition
```

Install dependencies:

```bash
pip install -r requirements.txt
```

(Optional) Add API tokens in `config.py` for higher rate limits.

---

## 🛠 Usage

### **Run Zenodo pipeline**
```bash
python pipeline.py --zenodo
```

### **Run DANS pipeline**
```bash
python pipeline.py --dans
```

The pipeline will:
- Query repositories  
- Download relevant datasets  
- Populate the SQLite database  
- Print a summary of harvested projects  

---

## 🧰 Tech Stack
- Python 3.x  
- SQLite  
- Dataverse API  
- Zenodo REST API  
- Requests / JSON  
- Multilingual keyword detection  

---

## 📜 License & Acknowledgments
These sections are included **only in the root README**, not in module‑level READMEs.

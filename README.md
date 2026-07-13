# 📘 **SeedingQDArchive: Automated Pipeline for Harvesting and Classifying Qualitative Research Datasets**

## 🌍 **1. Introduction**

QDArchive is an end-to-end pipeline designed to identify, retrieve, classify, and semantically organize **qualitative research datasets** from major open repositories.

The pipeline operates in two distinct phases:

1. **Acquisition:** Automatically harvests and filters datasets from **Zenodo** and **DANS Data Stations (Dataverse)**, identifying qualitative project files (NVivo, ATLAS.ti, MaxQDA, REFI-QDA) and textual materials (interviews, transcripts, field notes) across multiple languages.
2. **Classification:** Semantically indexes and maps the acquired data to the **ISIC Rev.5 (International Standard Industrial Classification) taxonomy** using dense vector embeddings, providing automated thematic organization by economic sector.

The pipeline maintains a structured **SQLite data model**, facilitating reproducible research, metadata standardization, and downstream discovery.

---

## ⚙️ **2. System Overview**

The pipeline is composed of highly modular components divided across the two functional phases:

### 📥 **Phase 1: Acquisition Components**

* **Configuration Layer (`data_acquisition/config.py`):** Defines repository API endpoints, authentication tokens, pagination controls, file-type lists, and multilingual query strings.
* **Utility Layer (`data_acquisition/utils.py`):** Houses shared mechanics for rate-limit management, parallel download threads, retry logic, and fallback language identification.
* **Database Layer (`data_acquisition/database.py`):** Implements the relational schema (`PROJECTS`, `FILES`, `KEYWORDS`, `PERSON_ROLE`, `LICENSES`) following the required output format specifications.
* **Repository Harvesters (`zenodo.py`, `dans.py`):** Domain-specific harvesters that interact with the Zenodo REST API and Dataverse API to discover, filter, and extract targets.
* **Acquisition Orchestrator (`data_acquisition/pipeline.py`):** Coordinates search queries, monitors process state, and prevents redundant downloads.

### 🧠 **Phase 2: Classification Components**

* **Configuration Layer (`data_classification/config.py`):** Configures embedding model targets, threshold filters, and paths to taxonomic reference materials.
* **Type Classifier (`data_classification/project_type.py`):** Evaluates the presence of qualitative materials to tag projects with operational categories (`QDA_PROJECT`, `QD_PROJECT`, or `OTHER`).
* **Embedding Utility (`data_classification/embedder.py`):** Interfaces with the `multilingual-e5-large` encoder model to calculate normalized, high-dimensional vector representations.
* **Feature Extractor (`data_classification/extractor.py`):** Safely parses and extracts structural textual preview data from document files (such as `.pdf` and `.docx`).
* **Context Builder (`data_classification/project_text.py`):** Synthesizes structural metadata (title, keywords, description) and extracted textual previews into unified documents for encoding.
* **Taxonomic Classifier (`data_classification/classifier.py`):** Executes semantic zero-shot matching using cosine-similarity calculations across ~80 distinct economic divisions of the ISIC Rev.5 taxonomy.
* **Diagnostic Evaluator (`data_classification/evaluate.py`):** Computes diagnostic telemetry on model classifications, outputting performance and consistency metrics.

---

## 🧠 **3. Data Acquisition Logic**

Each dataset discovered during repository querying is evaluated using a rigorous four-step decision framework:

```
                  [ Discovered Dataset ]
                            │
                            ▼
             / \  Yes
            /   \ ─────────────────► [ Download All Files ]
            \ QDA? /                 (NVivo, ATLAS.ti, MaxQDA)
             \   /
              \ /
               │ No
               ▼
             / \  Yes
            /   \ ─────────────────► [ Skip / Exclude Dataset ]
            \ Irrel?/                (Non-qualitative formats)
             \   /
              \ /
               │ No
               ▼
             / \  Yes
            / Qual\ ────────────────► [ Download Supporting Files ]
            \ Indic?/                (Transcripts, text surveys, notes)
             \   /
              \ /
               │ No
               ▼
       [ Skip / Exclude ]

```

This tiered evaluation ensures the local archive prioritizes substantive, operational qualitative materials.

---

## 🏷️ **4. Data Classification Logic**

Once datasets are written to the database, they undergo semantic categorization:

1. **Operational Categorization:** Projects are analyzed to determine their functional research type:
* `QDA_PROJECT`: Contains native qualitative analysis software project files.
* `QD_PROJECT`: Lacks dedicated QDA project containers but contains substantial raw qualitative text structures (transcripts, surveys, interview reports).
* `OTHER`: Standard datasets containing unrelated numerical, spatial, or audio-visual data.


2. **Taxonomic Target Precomputation:** The system ingests the ISIC Rev.5 JSON definitions, mapping textual descriptions of all ~80 economic divisions into dense embedding vectors.
3. **Compound Project Representation:** To maximize accuracy across multiple languages, the system constructs a cohesive narrative representation for each project, combining title, user-provided tags, descriptions, and structural content previews extracted from within the actual dataset files.
4. **Vector Embedding Search:** The compound project text is encoded with `multilingual-e5-large`. The system calculates cosine-similarity scores against the precomputed ISIC taxonomy vectors, mapping the primary and secondary economic classes to the database along with confidence scores.
5. **Hierarchical Back-propagation:** The classification propagates down to the file level. For critical qualitative files, individual embeddings are evaluated to track sub-topic distribution within complex, multi-file projects.

---

## 📂 **5. Output & Database Structure**

The pipeline outputs are designed to exist in a clean, self-documenting footprint:

### 📁 **Structured Download Tree**

```bash
downloads/
├── zenodo/
│   └── <project_id>/
│       ├── file1.pdf
│       ├── file2.docx
│       └── metadata.json
└── dans/
    └── <station_name>/
        └── <project_id>/
            └── (files)

```

### 🗃️ **Normalized SQLite Schema (`qdarchive.db`)**

The relational database tracks acquisitions and classifications using five core tables:

* **`PROJECTS`:** Core metadata table containing unique identifier fields (`id`, `title`, `description`, `language`, `doi`), functional assignment (`type`), the directory paths, and the semantic classification outcomes (`primary_class`, `secondary_class`, `similarity_score`).
* **`FILES`:** File-level tracking sheet mapping to `PROJECTS` containing name, detected type, download status, structural preview text, and individual file-level classification labels.
* **`KEYWORDS`:** Project-level metadata keywords parsed from source repository tags.
* **`PERSON_ROLE`:** Authors, contributors, and organizational curators associated with the submission.
* **`LICENSES`:** Terms of use parsed directly from the repositories.

---

## 🖥️ **6. Running the Pipeline**

### **Part 1: Harvesting & Database Seeding**

Navigate to the acquisition directory and run the orchestrator:

```bash
cd data_acquisition

# Run Zenodo collection
python pipeline.py --zenodo

# Run DANS collection
python pipeline.py --dans

# Run all platforms sequentially
python pipeline.py --all

```

### **Part 2: Semantic Classification & Diagnostics**

Navigate to the classification directory to execute the pipeline stages:

```bash
cd ../data_classification

# Step A: Perform project type categorization
python project_type.py

# Step B: Run semantic ISIC mapping
python run_classification.py

# Step C: Generate quality and diagnostic metrics
python evaluate.py

```

---

## 📊 **7. Diagnostic Evaluation & Limitations**

### **Quality Metrics**

The classification pipeline monitors output quality using three main metrics:

* **Stability Score:** Measures how classification changes when adjusting chunk limits and preview lengths during context generation.
* **Coherence Score:** Calculates semantic similarity between the project-level assignment and independent classifications calculated for its constituent files.
* **Classification Consistency:** Evaluates taxonomic alignment across multi-language equivalents of the same project context.

### **Limitations & Considerations**

* **Zero-Shot Embedding vs. Supervised Methods:** This pipeline utilizes a highly flexible zero-shot vector similarity matching approach, allowing it to easily accommodate future changes to taxonomic structures (such as moving from ISIC Rev.5 to a different standard). However, when compared to **supervised methods**, zero-shot classification can display lower precision in highly specialized or niche domains. If large, hand-labeled datasets are available, **supervised methods** should be trained to achieve higher categorical precision for stable, unchanging taxonomies.
* **QDA Container Enclosures:** Detailed textual content trapped inside specialized, proprietary, or password-protected QDA project file formats cannot be automatically parsed due to licensing and structural constraints. The system falls back to external metadata and accompanying text files in these scenarios.
* **Maximum File Size Constraints:** A hard limit of 100 MB per file is applied to prevent network timeouts and local storage exhaustion.

---

## 🗃️ **8. Data Sources & Citation**

QDArchive harvests publicly available research datasets from open-science infrastructures:

### 🧩 **Zenodo (CERN, OpenAIRE)**

Datasets are retrieved via the **Zenodo REST API** ([https://zenodo.org/api/records](https://zenodo.org/api/records)).

**Citation:**

> Zenodo (CERN). *Zenodo Research Data Repository*. Available at: [https://zenodo.org](https://zenodo.org)

### 🧩 **DANS Data Stations (KNAW, Dutch Research Council)**

Datasets are retrieved via the domain-specific **Dataverse API** installations ([https://dans.knaw.nl](https://dans.knaw.nl)).

**Citation:**

> DANS. *DANS Data Stations (Dataverse)*. Available at: [https://dans.knaw.nl](https://dans.knaw.nl)

### 🧾 **Dataset-Level Citations**

Every dataset harvested by QDArchive includes its own DOI and license information stored in the database. Users must cite **each dataset individually**, following the repository’s citation format. The pipeline preserves:

* DOI (concept or version)
* Authors, creators, and uploaders
* License identifiers and keywords

---

## ⚖️ **9. Ethical & Legal Considerations**

* **Public Access Only:** The pipeline exclusively targets publicly accessible records. Restricted-access datasets requiring specific authorization are skipped automatically.
* **License Maintenance:** Original licenses (CC-BY, CC0, and other open-source arrangements) are captured alongside file payloads to ensure downstream compliance.
* **Respectful Crawling:** Acquisition routines incorporate polite rate-limiting, honoring the hosting servers' capacity limits.

---

## 🙏 **Acknowledgments**

I would like to express my sincere gratitude to **Prof. Dr. Dirk Riehle, M.B.A.** for providing me with the opportunity to work on this project and for his continuous guidance throughout its development. His insights, feedback, and support were invaluable in shaping the direction and quality of this work.

# 📘 Part 2: ISIC Rev.5 Classification & Evaluation Pipeline  
*A semantic, zero‑shot classification system for mapping qualitative datasets to ISIC Rev.5 industry divisions.*

---

## 📄 Overview
The **ISIC Rev.5 Classification Pipeline** processes all harvested datasets from Part 1 and performs:

- Project type assignment  
- Semantic text embedding  
- Zero‑shot similarity‑based classification  
- ISIC Rev.5 ontology mapping  
- File‑level and project‑level classification  
- Stability, consistency, and coherence evaluation  
- Semantic interpretability analysis  

This module transforms raw qualitative datasets into structured, industry‑aligned insights using modern embedding‑based semantic similarity techniques.

---

## ✨ Features
- Automatic project type classification (`QDA_PROJECT`, `QD_PROJECT`, `OTHER_PROJECT`, `UNKNOWN`)  
- Zero‑shot classification using **multilingual-e5-large**  
- ISIC Rev.5 division taxonomy support  
- Project‑level text construction (metadata + extracted content)  
- File‑level classification for primary qualitative data  
- Automatic database schema extension  
- Stability, consistency, and coherence metrics  
- Semantic interpretability examples  
- Repository‑aware project ordering  
- Modular architecture for easy extension  

---

## 🧱 Folder Structure
```
data_classification/
│
├── README_classification.md     ← Documentation for Part 2
├── __init__.py                  ← Package initializer
│
├── project_type.py              ← Assigns project types (Step 1)
├── run_classification.py        ← Main ISIC classification pipeline (Step 2)
├── evaluate.py                  ← Evaluation metrics (Step 3)
│
├── classifier.py                ← Core ISIC classification logic
├── config.py                    ← Global configuration (paths, model, thresholds)
├── embedder.py                  ← Embedding utilities (chunking + mean pooling)
├── extractor.py                 ← Text extraction utilities (PDF, DOCX, TXT, QDA)
├── project_text.py              ← Project-level text construction
├── project_type.py              ← Project type classification module
├── isic.py                      ← ISIC Rev.5 taxonomy utilities
├── isic_divisions.json          ← ISIC Rev.5 division metadata
│
└── requirements.txt             ← Dependencies for Part 2
```

---

## 🔄 Pipeline Execution Order  
To run the full classification pipeline, follow this exact order:

### **1️⃣ Assign Project Types**
Classifies each project into:
- `QDA_PROJECT`  
- `QD_PROJECT`  
- `OTHER_PROJECT`  
- `UNKNOWN`

```bash
python project_type.py
```

### **2️⃣ Run ISIC Classification**
Performs:
- Project‑level text construction  
- Embedding generation  
- Zero‑shot ISIC ranking  
- File‑level classification  
- Database schema updates  

```bash
python run_classification.py
```

### **3️⃣ Evaluate Classification Results**
Computes:
- Project–File Consistency Score  
- Cluster Coherence  
- Stability Score  
- Semantic Interpretability Examples  
- Most common ISIC class per repository  

```bash
python evaluate.py
```

This order is required because:
- Project types influence classification priority  
- Classification results are needed for evaluation  

---

## 🧠 How It Works

### **1. Project Type Assignment**
`project_type.py` analyzes file extensions and metadata to categorize projects.  
This ensures QDA projects are processed first during classification.

---

### **2. Build Project-Level Text**
`project_text.py` constructs unified text blocks using:
- Metadata (title, description, keywords)  
- Extracted text from primary qualitative files  
- Lightweight previews from QDA containers  

---

### **3. Generate Semantic Embeddings**
Using **multilingual-e5-large**, the pipeline:
- Splits text into chunks  
- Prefixes chunks (`query:` / `passage:`)  
- Encodes each chunk  
- Mean‑pools embeddings  

---

### **4. Zero‑shot ISIC Rev.5 Classification**
`classifier.py` ranks each project against all ISIC division embeddings using cosine similarity.

Outputs:
- Primary ISIC class  
- Secondary ISIC class  
- Similarity score  
- Top‑k ranked candidates  

---

### **5. File-Level Classification**
Primary qualitative files (PDF, DOCX, TXT, CSV, etc.) are classified individually.

Used for:
- Stability scoring  
- Project–file consistency scoring  
- Fine‑grained semantic analysis  

---

### **6. Evaluation Metrics**
`evaluate.py` computes:

#### **Project–File Consistency Score**
Alignment between project‑level and file‑level predictions.

#### **Cluster Coherence**
Jaccard similarity of project titles within each ISIC class.

#### **Stability Score**
Measures how consistently files within a project fall into the same ISIC class.

#### **Semantic Interpretability Examples**
Representative project titles for top ISIC classes.

---

## 📦 Installation
Clone the repository:

```bash
git clone https://github.com/puni-ram48/SeedingQDArchive.git
cd SeedingQDArchive/data_classification
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 🛠 Usage

### **Run full pipeline**
```bash
python project_type.py
python run_classification.py
python evaluate.py
```

### **Evaluate specific repository**
```bash
python evaluate.py 1     # Zenodo
python evaluate.py 5     # DANS
```

---

## 🧰 Tech Stack
- Python 3.x  
- Sentence‑Transformers  
- HuggingFace embeddings  
- NumPy / Pandas  
- SQLite  
- pypdf / python‑docx  
- JSON taxonomy files  

---

## 📜 License & Acknowledgments
These sections are included **only in the root README**, not in module‑level READMEs.

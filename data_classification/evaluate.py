"""
Evaluation script for ISIC Rev.5 classification results.

Usage:
    python evaluate.py              # evaluate ALL repositories together
    python evaluate.py 1            # evaluate only repository_id = 1 (e.g. zenodo)
    python evaluate.py 5            # evaluate only repository_id = 5 (e.g. DANS)

Metrics:
    - Project–File Consistency Score
    - Cluster Coherence (Jaccard similarity_score_score of project titles per class)
    - Stability Score (file-level class stability within projects)
    - Semantic Interpretability Examples (titles per ISIC class)
    - Most Common Class Across All Projects (per repo)

Assumptions:
    - SQLite DB path and JSON path are defined in config.py:
        DB_FILE
        ISIC_JSON_PATH
    - Tables:
        projects(id, repository_id, title, primary_class)
        file_classification(project_id, file_name, primary_class, secondary_class, similarity_score)
"""

import sys
import sqlite3
import json
from collections import Counter, defaultdict

from config import DB_FILE, ISIC_JSON_PATH


# ---------- Utility functions ----------

def load_isic_divisions(json_path: str) -> dict:
    """Load ISIC divisions from JSON and return dict code -> (name, description)."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {entry["code"]: (entry["name"], entry["description"]) for entry in data}


def tokenize_title(title: str) -> set:
    """Simple tokenization for Jaccard similarity_score (lowercase, split on spaces)."""
    if not title:
        return set()
    return set(title.lower().split())


def jaccard_similarity_score(a: set, b: set) -> float:
    """Compute Jaccard similarity_score between two token sets."""
    if not a or not b:
        return 0.0
    inter = a & b
    union = a | b
    return len(inter) / len(union)


# ---------- Data loading ----------

def load_projects(conn, repository_id=None):
    """Load projects (optionally filtered by repository_id)."""
    cur = conn.cursor()
    if repository_id is None:
        rows = cur.execute(
            "SELECT id, repository_id, title, primary_class FROM projects"
        ).fetchall()
    else:
        rows = cur.execute(
            "SELECT id, repository_id, title, primary_class FROM projects WHERE repository_id = ?",
            (repository_id,),
        ).fetchall()

    projects = []
    for pid, rid, title, pclass in rows:
        projects.append(
            {
                "id": pid,
                "repository_id": rid,
                "title": title or "",
                "primary_class": str(pclass) if pclass is not None else None,
            }
        )
    return projects


def load_file_classifications(conn, project_ids):
    """Load file-level classifications for given project_ids."""
    if not project_ids:
        return {}

    cur = conn.cursor()
    placeholders = ",".join("?" for _ in project_ids)
    query = f"""
        SELECT project_id, file_name, primary_class, secondary_class, similarity_score
        FROM file_classification
        WHERE project_id IN ({placeholders})
    """
    rows = cur.execute(query, project_ids).fetchall()

    by_project = defaultdict(list)
    for pid, fname, pclass, sclass, sim in rows:
        by_project[pid].append(
            {
                "file_name": fname or "",
                "primary_class": str(pclass) if pclass is not None else None,
                "secondary_class": str(sclass) if sclass is not None else None,
                "similarity_score": float(sim) if sim is not None else 0.0,
            }
        )
    return by_project


# ---------- Metrics ----------

def compute_project_file_consistency(projects, file_by_project):
    """Project–File Consistency Score."""
    scores = []

    for proj in projects:
        pid = proj["id"]
        pclass = proj["primary_class"]
        files = file_by_project.get(pid, [])

        if not files or pclass is None:
            continue

        total = 0
        match = 0
        for f in files:
            fclass = f["primary_class"]
            if fclass is None:
                continue
            total += 1
            if fclass == pclass:
                match += 1

        if total > 0:
            scores.append(match / total)

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


def compute_cluster_coherence(projects):
    """Cluster Coherence using Jaccard similarity_score of titles."""
    titles_by_class = defaultdict(list)
    for proj in projects:
        pclass = proj["primary_class"]
        title = proj["title"]
        if pclass is None or not title:
            continue
        titles_by_class[pclass].append(title)

    coherence = []
    for code, titles in titles_by_class.items():
        if len(titles) < 2:
            continue

        token_sets = [tokenize_title(t) for t in titles]
        sims = []
        for i in range(len(token_sets)):
            for j in range(i + 1, len(token_sets)):
                sims.append(jaccard_similarity_score(token_sets[i], token_sets[j]))

        if sims:
            coherence.append((code, sum(sims) / len(sims)))

    coherence.sort(key=lambda x: x[1], reverse=True)
    return coherence


def compute_stability_score(projects, file_by_project):
    """Stability Score: max fraction of files in any single class."""
    stabilities = []

    for proj in projects:
        pid = proj["id"]
        files = file_by_project.get(pid, [])
        if not files:
            continue

        classes = [f["primary_class"] for f in files if f["primary_class"] is not None]
        if not classes:
            continue

        counts = Counter(classes)
        total = sum(counts.values())
        max_frac = max(counts.values()) / total
        stabilities.append(max_frac)

    if not stabilities:
        return 0.0

    return sum(stabilities) / len(stabilities)


def collect_semantic_examples(projects, top_n=10, per_class=5):
    """Semantic Interpretability Examples."""
    class_counts = Counter()
    titles_by_class = defaultdict(list)

    for proj in projects:
        pclass = proj["primary_class"]
        title = proj["title"]
        if pclass is None or not title:
            continue
        class_counts[pclass] += 1
        titles_by_class[pclass].append(title)

    top_classes = [code for code, _ in class_counts.most_common(top_n)]
    examples = {}
    for code in top_classes:
        examples[code] = titles_by_class[code][:per_class]

    return examples


# ---------- Main ----------

def main():
    # Parse optional repository_id argument
    repository_id = None
    if len(sys.argv) > 1:
        try:
            repository_id = int(sys.argv[1])
        except ValueError:
            print("Invalid repository_id argument. Use an integer (e.g., 1 or 5).")
            sys.exit(1)

    # Load ISIC divisions
    isic_info = load_isic_divisions(ISIC_JSON_PATH)

    # Connect to DB
    conn = sqlite3.connect(DB_FILE)

    # Load projects (optionally filtered by repository_id)
    projects = load_projects(conn, repository_id=repository_id)
    if not projects:
        print(f"No projects found for repository_id = {repository_id}.")
        conn.close()
        return

    project_ids = [p["id"] for p in projects]

    # Load file-level classifications
    file_by_project = load_file_classifications(conn, project_ids)

    # ---------- Compute metrics ----------

    # 1. Project–File Consistency
    consistency = compute_project_file_consistency(projects, file_by_project)
    print(f"Project–File Consistency Score: {consistency:.3f}\n")

    # 2. Cluster Coherence
    coherence = compute_cluster_coherence(projects)
    print("Cluster Coherence (Jaccard similarity_score of titles):")
    for code, score in coherence[:10]:
        name = isic_info.get(code, ("Unknown", ""))[0]
        print(f"ISIC {code} ({name}): {score:.3f}")
    print()

    # 3. Stability Score
    stability = compute_stability_score(projects, file_by_project)
    print(f"Stability Score: {stability:.3f}\n")

    # 4. Semantic Interpretability Examples
    examples = collect_semantic_examples(projects, top_n=10, per_class=5)
    print("Semantic Interpretability Examples:\n")
    for code, titles in examples.items():
        name, desc = isic_info.get(code, ("Unknown", ""))
        print(f"ISIC {code} ({name}):")
        for t in titles:
            print(f"  - {t}")
        print()

    # 5. Most common class across all projects (per repo)
    class_counts = Counter([p["primary_class"] for p in projects if p["primary_class"]])
    if class_counts:
        dominant_class, count = class_counts.most_common(1)[0]
        name, desc = isic_info.get(dominant_class, ("Unknown", ""))
        print("Most Common Class Across All Projects:")
        print(f"  ISIC {dominant_class} – {name}")
        print(f"  Description: {desc}")
        print(f"  Count: {count}\n")
    else:
        print("Most Common Class Across All Projects: No classes found.\n")

    conn.close()


if __name__ == "__main__":
    main()

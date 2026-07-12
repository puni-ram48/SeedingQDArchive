"""
Evaluation utilities for ISIC Rev.5 classification results.

This module computes several quality metrics for the unsupervised
semantic classifier, including:

1. Project–File Consistency Score
2. Cluster Coherence (Jaccard similarity of project titles)
3. Stability Score (project-level class appears in file-level top-3)
4. Similarity Score Distribution (project vs file embeddings)
5. Semantic Interpretability Examples (top titles per ISIC division)

These metrics help validate the robustness, coherence, and
interpretability of the classification pipeline.
"""

import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter, defaultdict

# ---------------------------------------------------------------------------
# Load project-level and file-level classification results
# ---------------------------------------------------------------------------
def load_results(db_path: str):
    """Load project-level and file-level classification tables from SQLite."""
    conn = sqlite3.connect(db_path)

    projects = pd.read_sql_query(
        """
        SELECT id, title, primary_class, secondary_class, similarity_score
        FROM projects
        WHERE primary_class IS NOT NULL
        """,
        conn,
    )

    files = pd.read_sql_query(
        """
        SELECT project_id, file_name, primary_class, similarity_score
        FROM file_classification
        """,
        conn,
    )

    conn.close()
    return projects, files
  
# ---------------------------------------------------------------------------
# 1. PROJECT–FILE CONSISTENCY SCORE
# ---------------------------------------------------------------------------
def compute_project_file_consistency(projects, files):
    """
    Measures how often the project-level ISIC class matches the majority
    file-level ISIC class for the same project.
    """
    consistent = 0
    total = 0

    grouped = files.groupby("project_id")

    for _, row in projects.iterrows():
        pid = row["id"]
        proj_class = row["primary_class"]

        if pid not in grouped.groups:
            continue

        file_classes = grouped.get_group(pid)["primary_class"].tolist()
        if not file_classes:
            continue

        majority = Counter(file_classes).most_common(1)[0][0]

        if majority == proj_class:
            consistent += 1

        total += 1

    return consistent / total if total > 0 else 0

# ---------------------------------------------------------------------------
# 2. CLUSTER COHERENCE (Jaccard similarity of project titles)
# ---------------------------------------------------------------------------
def compute_cluster_coherence(projects):
    """
    Computes average pairwise Jaccard similarity of project titles
    within each ISIC division cluster.
    """
    clusters = defaultdict(list)

    for _, row in projects.iterrows():
        clusters[row["primary_class"]].append(row["title"])

    coherence = {}

    for isic, titles in clusters.items():
        sims = []
        tokenized = [set(t.lower().split()) for t in titles]

        for i in range(len(tokenized)):
            for j in range(i + 1, len(tokenized)):
                inter = len(tokenized[i].intersection(tokenized[j]))
                union = len(tokenized[i].union(tokenized[j]))
                if union > 0:
                    sims.append(inter / union)

        coherence[isic] = np.mean(sims) if sims else 0.0

    return coherence

# ---------------------------------------------------------------------------
# 3. STABILITY SCORE
# ---------------------------------------------------------------------------
def compute_stability_score(projects, files):
    """
    Measures how often the project-level ISIC class appears in the
    top-3 most frequent file-level classes for the same project.
    """
    stable = 0
    total = 0

    grouped = files.groupby("project_id")

    for _, row in projects.iterrows():
        pid = row["id"]
        proj_class = row["primary_class"]

        if pid not in grouped.groups:
            continue

        file_classes = grouped.get_group(pid)["primary_class"].tolist()
        top3 = [c for c, _ in Counter(file_classes).most_common(3)]

        if proj_class in top3:
            stable += 1

        total += 1

    return stable / total if total > 0 else 0

# ---------------------------------------------------------------------------
# 4. SIMILARITY SCORE DISTRIBUTION
# ---------------------------------------------------------------------------
def plot_similarity_distribution(projects, files):
    """
    Plots histogram distributions of similarity scores for project-level
    and file-level embeddings.
    """
    plt.figure(figsize=(10, 5))
    plt.hist(projects["similarity_score"], bins=30, alpha=0.6, label="Project-level")
    plt.hist(files["similarity_score"], bins=30, alpha=0.6, label="File-level")
    plt.legend()
    plt.title("Similarity Score Distribution")
    plt.xlabel("Similarity")
    plt.ylabel("Frequency")
    plt.grid(alpha=0.3)
    plt.show()
  
# ---------------------------------------------------------------------------
# 5. SEMANTIC INTERPRETABILITY EXAMPLES
# ---------------------------------------------------------------------------
def print_cluster_examples(projects, top_n=5):
    """
    Prints example project titles for each ISIC division to help assess
    semantic interpretability of clusters.
    """
    clusters = defaultdict(list)

    for _, row in projects.iterrows():
        clusters[row["primary_class"]].append(row["title"])

    print("\nSemantic Interpretability Examples:")
    for isic, titles in clusters.items():
        print(f"\nISIC {isic}:")
        for t in titles[:top_n]:
            print(f"  - {t}")
          
# ---------------------------------------------------------------------------
# MAIN EXECUTION (optional)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
  """
    DB_FILE:
      SQLite database generated by the data_acquisition step.
      Contains project metadata, file metadata, and download status.
    """
    DB_PATH = r"23173040-sq26.db"

    projects, files = load_results(DB_PATH)

    # 1. Consistency
    consistency = compute_project_file_consistency(projects, files)
    print(f"Project–File Consistency Score: {consistency:.3f}")

    # 2. Coherence
    coherence_scores = compute_cluster_coherence(projects)
    print("\nCluster Coherence (Jaccard similarity of titles):")
    for isic, score in sorted(coherence_scores.items(), key=lambda x: -x[1])[:10]:
        print(f"ISIC {isic}: {score:.3f}")

    # 3. Stability
    stability = compute_stability_score(projects, files)
    print(f"\nStability Score: {stability:.3f}")

    # 4. Similarity distribution
    plot_similarity_distribution(projects, files)

    # 5. Interpretability examples
    print_cluster_examples(projects)

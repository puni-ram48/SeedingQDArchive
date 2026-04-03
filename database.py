"""
database.py 
5-table SQLite schema following professor's Data Acquisition Output Format
Tables: PROJECTS, FILES, KEYWORDS, PERSON_ROLE, LICENSES
"""

import sqlite3
from config import DB_FILE

def get_connection():
    """Get database connection"""
    return sqlite3.connect(DB_FILE)

def setup_database():
    """Create all 5 tables if they don't exist"""
    conn = get_connection()
    cursor = conn.cursor()

    # PROJECTS table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id                          INTEGER PRIMARY KEY AUTOINCREMENT,
            query_string                TEXT,
            repository_id               INTEGER NOT NULL,
            repository_url              TEXT NOT NULL,
            project_url                 TEXT NOT NULL,
            version                     TEXT,
            title                       TEXT NOT NULL,
            description                 TEXT,
            language                    TEXT,
            doi                         TEXT,
            upload_date                 TEXT,
            download_date               TEXT NOT NULL,
            download_repository_folder  TEXT NOT NULL,
            download_project_folder     TEXT NOT NULL,
            download_version_folder     TEXT,
            download_method             TEXT NOT NULL DEFAULT 'API-CALL',
            has_qda_file                INTEGER DEFAULT 0,
            download_complete           INTEGER DEFAULT 0
        )
    """)

        # FILES table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            file_name   TEXT NOT NULL,
            file_type   TEXT NOT NULL,
            file_size   INTEGER DEFAULT 0,              -- NEW: file size in bytes
            status      INTEGER DEFAULT 0,  -- 0=not downloaded, 1=downloaded, 2=skipped, 3=too large
            skip_reason TEXT,                           -- NEW: why was it skipped
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    # KEYWORDS table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keywords (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            keyword     TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    # PERSON_ROLE table
    # Role values: UPLOADER, AUTHOR, OWNER, CONTRIBUTOR, UNKNOWN
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS person_role (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            name        TEXT NOT NULL,
            role        TEXT NOT NULL DEFAULT 'UNKNOWN',
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    # LICENSES table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            license     TEXT NOT NULL,
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    """)

    # Indexes for faster lookups 
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_doi ON projects(doi)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_repo ON projects(repository_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_project ON files(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_project ON keywords(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_person_project ON person_role(project_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_licenses_project ON licenses(project_id)")

    conn.commit()
    print(f"Database ready: {DB_FILE}")
    print(f"Tables: projects, files, keywords, person_role, licenses")
    return conn

def project_exists(conn, doi, repository_id):
    """Check if a project with this DOI and repo is already in database"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM projects WHERE doi = ? AND repository_id = ?",
        (doi, repository_id)
    )
    result = cursor.fetchone()
    return result[0] if result else None

def save_project(conn, project_data):
    """
    Save a project and all related data to all 5 tables.

    project_data dict must contain:
        query_string, repository_id, repository_url, project_url,
        version, title, description, language, doi, upload_date,
        download_date, download_repository_folder, download_project_folder,
        download_version_folder, download_method, has_qda_file,
        download_complete,
        files: list of {file_name, file_type}
        keywords: list of keyword strings
        persons: list of {name, role}
        licenses: list of license strings
    """
    cursor = conn.cursor()

    # Insert into PROJECTS
    cursor.execute("""
        INSERT INTO projects (
            query_string, repository_id, repository_url, project_url,
            version, title, description, language, doi, upload_date,
            download_date, download_repository_folder, download_project_folder,
            download_version_folder, download_method, has_qda_file,
            download_complete
        ) VALUES (
            :query_string, :repository_id, :repository_url, :project_url,
            :version, :title, :description, :language, :doi, :upload_date,
            :download_date, :download_repository_folder, :download_project_folder,
            :download_version_folder, :download_method, :has_qda_file,
            :download_complete
        )
    """, project_data)

    project_id = cursor.lastrowid

        # Insert into FILES — one row per file
    for file_info in project_data.get("files", []):
        cursor.execute(
            "INSERT INTO files (project_id, file_name, file_type, file_size, status, skip_reason) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (project_id, 
             file_info["file_name"], 
             file_info["file_type"],
             file_info.get("file_size", 0),
             file_info.get("status", 0),
             file_info.get("skip_reason", None))
        )

    # Insert into KEYWORDS — one row per keyword (stored as-is per meeting notes)
    for keyword in project_data.get("keywords", []):
        if keyword and keyword.strip():
            cursor.execute(
                "INSERT INTO keywords (project_id, keyword) VALUES (?, ?)",
                (project_id, keyword.strip())
            )

    # Insert into PERSON_ROLE — one row per person
    for person in project_data.get("persons", []):
        if person.get("name"):
            cursor.execute(
                "INSERT INTO person_role (project_id, name, role) VALUES (?, ?, ?)",
                (project_id, person["name"], person.get("role", "UNKNOWN"))
            )

    # Insert into LICENSES — one row per license
    for license_str in project_data.get("licenses", []):
        if license_str and license_str.strip():
            cursor.execute(
                "INSERT INTO licenses (project_id, license) VALUES (?, ?)",
                (project_id, license_str.strip())
            )

    conn.commit()
    return project_id
    
# Export to CSV
def export_to_csv(conn):
    """Export all tables to CSV files"""
    import csv

    tables = ["projects", "files", "keywords", "person_role", "licenses"]
    for table in tables:
        out = f"qdarchive_{table}.csv"
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        with open(out, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(cols)
            writer.writerows(rows)
        print(f"Exported {table} → {out} ({len(rows)} rows)")


# Print database summary 
def print_summary(conn):
    """Print a summary of what is in the database"""
    cursor = conn.cursor()
    print("\n" + "="*60)
    print("DATABASE SUMMARY")
    print("="*60)

    cursor.execute("SELECT COUNT(*) FROM projects")
    print(f"  Total projects:    {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM projects WHERE has_qda_file=1")
    print(f"  With QDA files:    {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM files")
    print(f"  Total files:       {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM keywords")
    print(f"  Total keywords:    {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM person_role")
    print(f"  Total persons:     {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM licenses")
    print(f"  Total licenses:    {cursor.fetchone()[0]}")

    print(f"\n  By repository:")
    cursor.execute("""
        SELECT repository_id, COUNT(*) as cnt
        FROM projects
        GROUP BY repository_id
        ORDER BY repository_id
    """)
    repo_names = {1: "Zenodo", 5: "DANS"}
    for repo_id, count in cursor.fetchall():
        name = repo_names.get(repo_id, f"Repo {repo_id}")
        print(f"    {name:<20} {count} projects")

    print(f"\n  By license:")
    cursor.execute("""
        SELECT license, COUNT(*) as cnt
        FROM licenses
        GROUP BY license
        ORDER BY cnt DESC
        LIMIT 10
    """)
    for lic, count in cursor.fetchall():
        print(f"    {lic:<25} {count}")

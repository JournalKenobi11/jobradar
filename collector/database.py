"""Database Access Layer Module.

Provides database connection retry patterns, table initialization hooks,
and record insertion services for Postgres.
"""

import time
import psycopg2
from datetime import datetime
import config

def log_inline(message, level="INFO"):
    """Quick localized log formatter."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}", flush=True)

def get_db_connection():
    """Establishes and returns a connection to the PostgreSQL Database.

    Implements a resilient retry strategy to handle database start-up delays
    commonly encountered in containerized environments.

    Returns:
        psycopg2.extensions.connection: An active PostgreSQL connection object.

    Raises:
        Exception: If the database is unreachable after maximum retry threshold.
    """
    max_retries = 5
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=config.DB_HOST,
                port=config.DB_PORT,
                database=config.DB_NAME,
                user=config.DB_USER,
                password=config.DB_PASSWORD
            )
            return conn
        except Exception as e:
            log_inline(
                f"Database connection attempt {i + 1}/{max_retries} failed: {e}",
                level="WARNING"
            )
            time.sleep(3)
    raise Exception("Could not connect to database after several retries.")

def init_db():
    """Initializes schema tables and indexes if they do not exist.

    Sets up structural schemas for the 'jobs', 'skills_daily',
    'skills_trend', and 'word_frequency' tables.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # --------------------------------------------------------
    # Create master Jobs schema
    # --------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            company TEXT,
            title TEXT,
            location TEXT,
            description TEXT,
            url TEXT,
            source TEXT,
            posted_date DATE,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------------------------
    # Daily aggregation tables
    # --------------------------------------------------------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS skills_daily (
            date DATE,
            skill TEXT,
            count INTEGER,
            rank INTEGER,
            PRIMARY KEY (date, skill)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS skills_trend (
            skill TEXT,
            date DATE,
            count INTEGER,
            PRIMARY KEY (skill, date)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS word_frequency (
            word TEXT,
            date DATE,
            count INTEGER,
            PRIMARY KEY (word, date)
        )
    """)

    # --------------------------------------------------------
    # Automatic schema migrations
    # Safe to run every startup
    # --------------------------------------------------------

    # Per-job extracted skills
    cur.execute("""
        ALTER TABLE jobs
        ADD COLUMN IF NOT EXISTS extracted_skills TEXT;
    """)

    # Skill category for analytics
    cur.execute("""
        ALTER TABLE skills_daily
        ADD COLUMN IF NOT EXISTS category TEXT;
    """)

    # --------------------------------------------------------
    # Performance indexes
    # --------------------------------------------------------
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_posted_date
        ON jobs(posted_date)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_company
        ON jobs(company)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_jobs_source
        ON jobs(source)
    """)

    conn.commit()
    cur.close()
    conn.close()
    log_inline("Database initialized successfully.")

def save_jobs(jobs):
    """Inserts batch collections of jobs into Postgres.

    Uses an ON CONFLICT DO NOTHING block based on job_id to prevent double counting.

    Args:
        jobs (list[dict]): Standardized scraped job dictionaries containing
            job_id, company, title, location, description, url, source, and posted_date.
    """
    if not jobs:
        return

    conn = get_db_connection()
    cur = conn.cursor()

    saved_count = 0
    for job in jobs:
        try:
            cur.execute("""
                INSERT INTO jobs (job_id, company, title, location, description, url, source, posted_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id) DO NOTHING
            """, (
                job['job_id'],
                job['company'],
                job['title'],
                job['location'],
                job.get('description', ''),
                job.get('url', ''),
                job['source'],
                job['posted_date']
            ))
            if cur.rowcount > 0:
                saved_count += 1
        except Exception as e:
            log_inline(f"Error saving job: {e}", level="ERROR")

    conn.commit()
    cur.close()
    conn.close()
    log_inline(f"Saved {saved_count} new jobs.")
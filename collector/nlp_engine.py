"""NLP Extraction Engine Module.

Handles loading ML model snapshots from Hugging Face Hub, compiling the
spaCy pipelines, and extracting skills from unstructured job postings.
"""

import time
from collections import Counter
from datetime import datetime
import spacy
from huggingface_hub import snapshot_download
import database

# Local log tracker formatting
def log_inline(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}", flush=True)

# ============================================================
# BOOTSTRAP MODEL LOADING
# ============================================================
log_inline("Downloading pipeline snapshot from Hugging Face Hub...")
start_time = time.time()

model_path = snapshot_download(
    repo_id="amjad-awad/skill-extractor",
    repo_type="model"
)

log_inline(f"Resolved Model path: {model_path}")
log_inline("Loading spaCy pipeline environment...")

# Initialize NLP Pipeline globally
nlp = spacy.load(model_path)
log_inline(f"NLP Model loaded successfully ({time.time() - start_time:.2f} sec)")


def extract_skills_spacy(text):
    """Parses text payloads using spaCy NER architecture to extract skill tags.

    Args:
        text (str): Combined text string containing job title and description.

    Returns:
        list[str]: Unique extracted entity names containing the 'SKILL' category label.
    """
    if not text or len(text) < 10:
        return []

    doc = nlp(text)
    skills = [ent.text for ent in doc.ents if "SKILL" in ent.label_]
    return list(set(skills))


def compute_daily_skills():
    """Aggregates all listings scraped today and analyzes raw frequencies.

    Extracts trending skill tokens and updates frequency rankings within
    the PostgreSQL analytics tables.
    """
    conn = database.get_db_connection()
    cur = conn.cursor()

    # Query all records posted on the current date
    cur.execute("""
        SELECT job_id, title, description FROM jobs
        WHERE posted_date = CURRENT_DATE
    """)
    jobs = cur.fetchall()

    if not jobs:
        log_inline("No jobs collected today. Skipping daily analytics computation.")
        cur.close()
        conn.close()
        return

    skill_counts = {}
    all_skill_terms = []

    # Process and tokenize bodies
    for job_id, title, description in jobs:
        text = f"{title} {description if description else ''}"
        skills = extract_skills_spacy(text)
        all_skill_terms.extend(skills)
        for skill in skills:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1

    if not skill_counts:
        log_inline("No skills extracted from today's jobs.")
        cur.close()
        conn.close()
        return

    # Sort skills by occurrence counts
    sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)

    # Insert top 200 daily ranked statistics
    for rank, (skill, count) in enumerate(sorted_skills[:200], 1):
        cur.execute("""
            INSERT INTO skills_daily (date, skill, count, rank)
            VALUES (CURRENT_DATE, %s, %s, %s)
            ON CONFLICT (date, skill) DO UPDATE SET
                count = EXCLUDED.count,
                rank = EXCLUDED.rank
        """, (skill, count, rank))

    # Compile and store general word trend distribution mapping (Up to 300)
    skill_counter = Counter(all_skill_terms)
    for skill, count in skill_counter.most_common(300):
        cur.execute("""
            INSERT INTO word_frequency (word, date, count)
            VALUES (%s, CURRENT_DATE, %s)
            ON CONFLICT (word, date) DO UPDATE SET
                count = EXCLUDED.count
        """, (skill, count))

    conn.commit()
    cur.close()
    conn.close()
    log_inline(f"Computed {len(sorted_skills)} unique skills from daily pipeline run.")
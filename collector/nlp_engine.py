import re
import time
from collections import Counter
from datetime import datetime

import spacy
from spacy.matcher import PhraseMatcher
from huggingface_hub import snapshot_download

import database


def log_inline(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}", flush=True)


# ============================================================
# CANONICAL DS/ML SKILLS TAXONOMY
# ============================================================
# category -> { canonical_display_name: [alias phrases to match, lowercased] }
# This is the part worth tuning over time - add new libraries/tools here as
# they come up in job postings rather than hoping the NER model catches them.

SKILLS_TAXONOMY = {
    "Programming Languages": {
        "Python": ["python"],
        "SQL": ["sql", "postgresql", "mysql", "t-sql", "pl/sql"],
        "C++": ["c++", "cpp"],
        "JavaScript": ["javascript", "js"],
        "TypeScript": ["typescript"],
        "R": ["r programming language", "r language"],
        "Scala": ["scala"],
        "Java": ["java"],
    },
    "Data Manipulation & Analysis": {
        "NumPy": ["numpy"],
        "Pandas": ["pandas"],
        "EDA": ["eda", "exploratory data analysis"],
        "Data Preprocessing": ["data preprocessing", "data pre-processing"],
        "Data Pipelines": ["data pipeline", "data pipelines"],
        "Data Engineering": ["data engineering"],
        "Feature Engineering": ["feature engineering"],
        "Data Wrangling": ["data wrangling", "data cleaning", "data munging"],
        "ETL": ["etl", "extract transform load"],
    },
    "Machine Learning Frameworks": {
        "TensorFlow": ["tensorflow", "tf.keras"],
        "PyTorch": ["pytorch"],
        "Scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
        "Keras": ["keras"],
        "XGBoost": ["xgboost", "xgb"],
        "LightGBM": ["lightgbm"],
        "CatBoost": ["catboost"],
    },
    "Deep Learning & AI": {
        "Machine Learning": ["machine learning"],
        "Deep Learning": ["deep learning"],
        "NLP": ["nlp", "natural language processing"],
        "Computer Vision": ["computer vision"],
        "CNN": ["cnn", "convolutional neural network"],
        "RAG": ["retrieval-augmented generation", "retrieval augmented generation", "rag"],
        "LLMs": ["llm", "large language models", "genai", "generative ai"],
        "Transformers": ["transformers", "hugging face", "huggingface"],
        "Neural Networks": ["neural networks", "rnn", "lstm"],
    },
    "Statistics & Modeling": {
        "Statistics": ["statistics", "statistical modeling", "statistical analysis"],
        "Hypothesis Testing": ["hypothesis testing"],
        "A/B Testing": ["a/b testing", "ab testing"],
        "Regression": ["regression analysis", "linear regression", "logistic regression"],
        "Time-Series Analysis": ["time series", "time-series", "time-series forecasting", "forecasting"],
        "Calculus": ["calculus"],
    },
    "Visualization": {
        "Matplotlib": ["matplotlib"],
        "Seaborn": ["seaborn"],
        "Tableau": ["tableau"],
        "Power BI": ["power bi", "powerbi"],
        "Plotly": ["plotly"],
        "Streamlit": ["streamlit"],
    },
    "Big Data & Cloud": {
        "Spark": ["spark", "pyspark", "apache spark"],
        "Hadoop": ["hadoop"],
        "AWS": ["aws", "amazon web services", "sagemaker"],
        "GCP": ["gcp", "google cloud", "bigquery", "vertex ai"],
        "Azure": ["azure", "azure ml"],
        "Databricks": ["databricks"],
        "Snowflake": ["snowflake"],
    },
    "Web Frameworks & APIs": {
        "Flask": ["flask", "flaskapi", "flask api"],
        "FastAPI": ["fastapi", "fast api"],
    },
    "Astronomy & Scientific Computing": {
        "Astropy": ["astropy"],
        "SciPy": ["scipy"],
        "HEASoft": ["heasoft"],
        "Astrophysics": ["astrophysics"],
        "Astronomy": ["astronomy"],
        "Physics": ["physics"],
    },
    "Systems & Hardware": {
        "CPU Architecture": ["cpu architecture"],
        "CPU Microbenchmarking": ["cpu microbenchmarking", "microbenchmarking"],
        "Linux Command Line": ["linux command line", "linux commandline", "shell scripting", "bash scripting"],
        "Home Server Setup": ["home server", "self-hosting", "self hosting"],
    },
    "Dev Tools & MLOps": {
        "Docker": ["docker"],
        "Kubernetes": ["kubernetes", "k8s"],
        "Git": ["git", "github", "gitlab"],
        "Conda": ["conda", "anaconda", "miniconda"],
        "Poetry": ["poetry"],
        "Airflow": ["airflow"],
        "MLflow": ["mlflow"],
        "CI/CD": ["ci/cd", "continuous integration"],
    },
}

# Phrases inside this many characters of a match will suppress it - catches
# "TensorFlow not required" / "PyTorch is a nice-to-have but not mandatory"
# type phrasing so a skill mentioned only to be excluded isn't counted as a
# real requirement.
import html as html_lib

# Generic words the fallback NER model tends to false-positive on. These
# aren't skills, just common English words that happen to appear near
# technical content in job postings.
FALLBACK_BLOCKLIST = {
    "engineering", "designing", "design", "code", "coding", "development",
    "developing", "building", "working", "experience", "team", "role",
    "looking", "strong", "solid", "using", "skills", "science", "technology",
    "platform", "product", "project", "projects", "solutions", "systems",
    "tools", "knowledge", "understanding", "ability", "years", "work",
}


def _clean_text(text):
    """Strips HTML tags and decodes HTML entities from a title/description.

    Job descriptions (especially from Greenhouse) come back as raw HTML.
    Without this, stray fragments like "&lt;p&gt;The..." get fed straight
    into the NLP model and show up as garbage "skills" like "lt;p>The".
    """
    if not text:
        return ""
    text = html_lib.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_plausible_fallback_skill(entity_text):
    """Quality filter for NER-fallback matches outside the fixed taxonomy.

    The fallback model is noisy - it fires on generic English words as
    often as real skills. Only accept an entity if it looks tool/tech-like:
    an acronym, contains tech-specific characters, or is multi-word (real
    skill phrases are rarely single common words).
    """
    text = entity_text.strip()
    if not text or len(text) < 2:
        return False
    if text.lower() in FALLBACK_BLOCKLIST:
        return False
    # Reject if it's just a single common lowercase word with no tech markers
    has_tech_chars = bool(re.search(r"[.+#/\d]", text))
    is_acronym = text.isupper() and 2 <= len(text) <= 6
    is_multi_word = len(text.split()) > 1
    if not (has_tech_chars or is_acronym or is_multi_word):
        return False
    return True


NEGATION_WINDOW_CHARS = 45
NEGATION_CUES = [
    "not required", "not necessary", "not mandatory", "no experience",
    "nice to have but not", "without the need for", "n/a",
]


# ============================================================
# BOOTSTRAP MODEL LOADING (fallback NER pass for anything outside
# the fixed taxonomy above)
# ============================================================
log_inline("Downloading pipeline snapshot from Hugging Face Hub...")
start_time = time.time()

model_path = snapshot_download(
    repo_id="amjad-awad/skill-extractor",
    repo_type="model"
)

log_inline(f"Resolved Model path: {model_path}")
log_inline("Loading spaCy pipeline environment...")

nlp = spacy.load(model_path)
log_inline(f"NLP Model loaded successfully ({time.time() - start_time:.2f} sec)")


def _build_skill_matcher():
    """Builds a PhraseMatcher covering every alias in SKILLS_TAXONOMY.

    Match IDs are encoded as "category::canonical_name" so a single lookup
    on match gives both the display name and its category.
    """
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    for category, skills in SKILLS_TAXONOMY.items():
        for canonical, aliases in skills.items():
            patterns = [nlp.make_doc(alias) for alias in aliases]
            matcher.add(f"{category}::{canonical}", patterns)
    return matcher


skill_matcher = _build_skill_matcher()
log_inline(f"Skill taxonomy matcher built ({sum(len(v) for v in SKILLS_TAXONOMY.values())} canonical skills)")


def _is_negated(text, start_char, end_char):
    window = text[max(0, start_char - NEGATION_WINDOW_CHARS): end_char + NEGATION_WINDOW_CHARS].lower()
    return any(cue in window for cue in NEGATION_CUES)


def extract_skills(text):
    """Extracts (canonical_skill, category) pairs from a text payload.

    Two passes:
      1. Taxonomy PhraseMatcher - high-precision match against a curated
         list of DS/ML libraries, tools, and concepts. This is what
         reliably catches things like "NumPy", "TensorFlow", "EDA" instead
         of depending entirely on the NER model recognizing them.
      2. NER fallback - catches skill-like entities outside the fixed
         taxonomy (useful for spotting new/unlisted tools trending in
         postings), tagged under category "Other" for manual review.

    Matches inside a negation window (e.g. "TensorFlow not required") are
    dropped rather than counted as a real requirement.

    Returns:
        list[tuple[str, str]]: (canonical_skill_name, category) pairs,
        deduplicated within this text (taxonomy match wins over NER fallback
        if both find the same term).
    """
    if not text or len(text) < 10:
        return []

    text = _clean_text(text)
    if len(text) < 10:
        return []

    doc = nlp(text)
    found = {}          # canonical (as-is) -> category
    found_lower = set() # lowercased canonical names, for case-insensitive dedup

    for match_id, start, end in skill_matcher(doc):
        span = doc[start:end]
        category, canonical = nlp.vocab.strings[match_id].split("::", 1)
        if _is_negated(text, span.start_char, span.end_char):
            continue
        found[canonical] = category
        found_lower.add(canonical.lower())

    for ent in doc.ents:
        if "SKILL" in ent.label_:
            candidate = ent.text.strip()
            if not candidate:
                continue
            # Already covered by a taxonomy match under any casing/alias -
            # this is what was causing "Machine Learning" and "machine
            # learning" to show up as two separate bars.
            if candidate.lower() in found_lower:
                continue
            if not _is_plausible_fallback_skill(candidate):
                continue
            if _is_negated(text, ent.start_char, ent.end_char):
                continue
            found[candidate] = "Other"
            found_lower.add(candidate.lower())

    return list(found.items())


def tag_missing_jobs():
    """Extracts and persists a per-job skill list for any job not yet tagged.

    This is what makes profile-match possible on the dashboard side without
    loading spaCy/the HF model there too - the dashboard just reads
    jobs.extracted_skills and does a plain set comparison against a known
    skill list, which is cheap. This function is the only place the actual
    NLP extraction happens per-job.

    Returns:
        int: number of jobs tagged this run.
    """
    conn = database.get_db_connection()
    cur = conn.cursor()

    # NOTE: assumes a `jobs.extracted_skills TEXT` column exists. If not:
    #   ALTER TABLE jobs ADD COLUMN extracted_skills TEXT;
    cur.execute("""
        SELECT job_id, title, description FROM jobs
        WHERE extracted_skills IS NULL
    """)
    untagged = cur.fetchall()

    if not untagged:
        cur.close()
        conn.close()
        return 0

    for job_id, title, description in untagged:
        title = title or ""
        description = description or ""
        combined = dict(extract_skills(title) + extract_skills(description))
        skill_names = sorted(combined.keys())

        cur.execute("""
            UPDATE jobs SET extracted_skills = %s WHERE job_id = %s
        """, (",".join(skill_names), job_id))

    conn.commit()
    cur.close()
    conn.close()
    log_inline(f"Tagged {len(untagged)} previously-untagged jobs with extracted_skills.")
    return len(untagged)


def compute_daily_skills():
    """Aggregates all listings scraped today and analyzes raw frequencies.

    Extracts trending skill tokens (with category + context-aware
    negation filtering) and updates frequency rankings within the
    PostgreSQL analytics tables. Skills mentioned in the job title are
    weighted 2x relative to description-only mentions, since a title
    mention is a much stronger relevance signal.

    Also backfills jobs.extracted_skills for any job missing it, via
    tag_missing_jobs(), so the dashboard's profile-match feature has
    per-job skill data to compare against.
    """
    tag_missing_jobs()

    conn = database.get_db_connection()
    cur = conn.cursor()

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

    TITLE_WEIGHT = 2

    skill_counts = {}       # canonical -> weighted count
    skill_categories = {}   # canonical -> category
    all_skill_terms = []    # for word_frequency table (unweighted, flat)

    for job_id, title, description in jobs:
        title = title or ""
        description = description or ""

        title_skills = extract_skills(title)
        desc_skills = extract_skills(description)

        # Merge, weighting title mentions higher
        seen_this_job = {}
        for skill, category in title_skills:
            seen_this_job[skill] = category
            skill_counts[skill] = skill_counts.get(skill, 0) + TITLE_WEIGHT
            skill_categories[skill] = category
            all_skill_terms.append(skill)

        for skill, category in desc_skills:
            if skill in seen_this_job:
                continue  # already counted via title at higher weight
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
            skill_categories[skill] = category
            all_skill_terms.append(skill)

    if not skill_counts:
        log_inline("No skills extracted from today's jobs.")
        cur.close()
        conn.close()
        return

    sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)

    # NOTE: this assumes skills_daily has a `category` column. If it
    # doesn't yet, run:
    #   ALTER TABLE skills_daily ADD COLUMN category TEXT;
    for rank, (skill, count) in enumerate(sorted_skills[:200], 1):
        category = skill_categories.get(skill, "Other")
        cur.execute("""
            INSERT INTO skills_daily (date, skill, category, count, rank)
            VALUES (CURRENT_DATE, %s, %s, %s, %s)
            ON CONFLICT (date, skill) DO UPDATE SET
                category = EXCLUDED.category,
                count = EXCLUDED.count,
                rank = EXCLUDED.rank
        """, (skill, category, count, rank))

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
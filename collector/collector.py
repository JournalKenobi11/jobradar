import psycopg2
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
import os
import time
import sys
import spacy
from collections import Counter
import re

from greenhouse import collect_greenhouse
from lever import collect_lever
from workday import collect_workday_public as collect_workday

DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'jobradar_db')
DB_USER = os.getenv('DB_USER', 'jobradar')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'jobradar123')

# Load spaCy model (will be installed in Dockerfile)
# Using the small model for speed, or the large model for better accuracy
nlp = spacy.load("en_core_web_sm")

# ============================================================
# ROLE & LOCATION FILTERING
# ============================================================
ROLE_KEYWORDS = [
    'data scientist', 'data analyst', 'ml engineer',
    'machine learning engineer', 'data engineer', 'ai engineer',
    'research scientist', 'applied scientist', 'data architect',
    'astrophysicist', 'astronomer', 'scientific programmer',
    'scientific computing', 'hpc', 'computational scientist'
]

LOCATIONS = [
    'mumbai', 'pune', 'bangalore', 'hyderabad', 'chennai',
    'delhi', 'gurgaon', 'noida', 'india', 'remote', 'hybrid'
]

def get_db_connection():
    max_retries = 5
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            return conn
        except Exception as e:
            print(f"  DB connection attempt {i+1}/{max_retries} failed: {e}")
            time.sleep(3)
    raise Exception("Could not connect to database")

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
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
    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_posted_date ON jobs(posted_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)")
    
    conn.commit()
    cur.close()
    conn.close()
    print("  Database initialized")

def is_relevant(title, location):
    """Check if job matches your target roles + locations."""
    title_lower = title.lower()
    location_lower = location.lower()
    
    role_match = any(k in title_lower for k in ROLE_KEYWORDS)
    if not role_match:
        return False
    
    location_match = any(k in location_lower for k in LOCATIONS)
    return location_match

def extract_skills_spacy(text):
    """
    Extract skills from text using spaCy NLP.
    Returns ALL skills found, not just one.
    """
    if not text or len(text) < 10:
        return []
    
    # Process the text with spaCy
    doc = nlp(text.lower())
    
    skills = set()
    
    # 1. Extract noun chunks (phrases like "machine learning", "data science")
    for chunk in doc.noun_chunks:
        chunk_text = chunk.text.strip()
        # Keep chunks between 2 and 40 characters
        if 2 < len(chunk_text) < 40:
            # Must contain at least one noun or proper noun
            if any(token.pos_ in {"NOUN", "PROPN"} for token in chunk):
                skills.add(chunk_text)
    
    # 2. Extract individual nouns and proper nouns
    for token in doc:
        if token.pos_ in {"NOUN", "PROPN"}:
            if 2 < len(token.text) < 20 and not token.is_stop:
                skills.add(token.text)
    
    # 3. Extract 2-word compounds
    for i in range(len(doc) - 1):
        token1 = doc[i]
        token2 = doc[i + 1]
        if token1.pos_ in {"NOUN", "PROPN"} and token2.pos_ in {"NOUN", "PROPN"}:
            phrase = f"{token1.text} {token2.text}"
            if 4 < len(phrase) < 30:
                skills.add(phrase)
        
        # 3-word compounds
        if i < len(doc) - 2:
            token3 = doc[i + 2]
            if (token1.pos_ in {"NOUN", "PROPN"} and 
                token2.pos_ in {"NOUN", "PROPN"} and 
                token3.pos_ in {"NOUN", "PROPN"}):
                phrase = f"{token1.text} {token2.text} {token3.text}"
                if 6 < len(phrase) < 40:
                    skills.add(phrase)
    
    # 4. Extract common technical skills (hardcoded fallback)
    technical_skills = [
        'python', 'sql', 'java', 'c++', 'javascript', 'typescript',
        'react', 'angular', 'vue', 'node.js', 'express', 'django',
        'flask', 'spring', 'docker', 'kubernetes', 'aws', 'azure',
        'gcp', 'linux', 'git', 'jenkins', 'ci/cd', 'terraform',
        'ansible', 'puppet', 'chef', 'nginx', 'apache', 'mysql',
        'postgresql', 'mongodb', 'redis', 'elasticsearch', 'kafka',
        'spark', 'hadoop', 'airflow', 'databricks', 'snowflake',
        'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch',
        'keras', 'machine learning', 'deep learning', 'nlp', 'computer vision',
        'llm', 'rag', 'langchain', 'fine-tuning', 'mlflow',
        'data science', 'data engineering', 'etl', 'data pipeline',
        'mlops', 'fastapi', 'streamlit', 'gradio', 'pytest'
    ]
    
    for skill in technical_skills:
        if skill in text.lower():
            skills.add(skill)
    
    # 5. Remove common non-skills
    common_words = {
        'experience', 'degree', 'bachelor', 'master', 'phd', 'science',
        'technology', 'engineering', 'mathematics', 'statistics', 'computer',
        'software', 'hardware', 'system', 'design', 'development',
        'analysis', 'research', 'team', 'work', 'project', 'role', 'position',
        'senior', 'junior', 'lead', 'manager', 'director', 'head', 'principal',
        'staff', 'expert', 'analyst', 'architect', 'developer', 'engineer',
        'scientist', 'researcher', 'consultant', 'specialist', 'solutions',
        'platform', 'infrastructure', 'architecture', 'framework', 'library',
        'tool', 'tools', 'technologies', 'services', 'service',
        'cloud', 'server', 'client', 'database', 'analytics', 'insights',
        'business', 'product', 'strategy', 'operations', 'support', 'maintenance',
        'performance', 'security', 'compliance', 'quality', 'testing',
        'deployment', 'production', 'environment', 'agile', 'scrum',
        'monitoring', 'logging', 'alerting', 'dashboard', 'reporting', 'visualization',
        'communication', 'management', 'leadership', 'teamwork', 'collaboration',
        'problem', 'solving', 'critical', 'thinking', 'analytical', 'attention',
        'detail', 'organization', 'planning', 'prioritization', 'time', 'flexibility',
        'adaptability', 'creativity', 'innovation', 'initiative', 'self', 'motivated',
        'interpersonal', 'presentation', 'negotiation', 'persuasion', 'influence'
    }
    
    # Remove common words
    filtered_skills = set()
    for skill in skills:
        skill_lower = skill.lower()
        if skill_lower not in common_words:
            filtered_skills.add(skill)
    
    # Convert to list and return
    return list(filtered_skills)

def save_jobs(jobs):
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
            print(f"  Error saving job: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    print(f"  Saved {saved_count} new jobs")

def compute_daily_skills():
    """
    Compute skill rankings for today using spaCy NLP.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get today's jobs
    cur.execute("""
        SELECT job_id, title, description FROM jobs
        WHERE posted_date = CURRENT_DATE
    """)
    
    jobs = cur.fetchall()
    
    if not jobs:
        print("  No jobs today, skipping skill computation")
        cur.close()
        conn.close()
        return
    
    # Extract skills from all jobs
    skill_counts = {}
    all_skill_terms = []
    
    for job_id, title, description in jobs:
        text = f"{title} {description if description else ''}"
        skills = extract_skills_spacy(text)
        all_skill_terms.extend(skills)
        for skill in skills:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
    
    if not skill_counts:
        print("  No skills extracted")
        cur.close()
        conn.close()
        return
    
    # Sort by frequency
    sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Save top 200 skills to skills_daily
    for rank, (skill, count) in enumerate(sorted_skills[:200], 1):
        cur.execute("""
            INSERT INTO skills_daily (date, skill, count, rank)
            VALUES (CURRENT_DATE, %s, %s, %s)
            ON CONFLICT (date, skill) DO UPDATE SET
                count = EXCLUDED.count,
                rank = EXCLUDED.rank
        """, (skill, count, rank))
    
    # Save word frequency for trend analysis
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
    print(f"  Computed {len(sorted_skills)} skills dynamically via NLP")

def collect_all():
    print(f"\n[{datetime.now()}] ===== Starting Collection =====")
    
    companies = {
        'greenhouse': [
            ("Razorpay", "razorpay"),
            ("Postman", "postman"),
            ("Fractal Analytics", "fractal-analytics"),
            ("Quantiphi", "quantiphi"),
            ("Tiger Analytics", "tiger-analytics"),
            ("ZS Associates", "zs-associates"),
        ],
        'lever': [
            ("Zerodha", "zerodha"),
            ("Groww", "groww"),
            ("CRED", "cred"),
            ("Meesho", "meesho"),
            ("Swiggy", "swiggy"),
        ],
        'workday': [
            ("NVIDIA", "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"),
            ("Microsoft", "https://microsoft.wd1.myworkdayjobs.com/en-US/MSFTJobs"),
            ("Amazon", "https://amazon.wd1.myworkdayjobs.com/en-US/External"),
            ("JPMorgan Chase", "https://jpmchase.wd1.myworkdayjobs.com/en-US/External"),
            ("Morgan Stanley", "https://morganstanley.wd1.myworkdayjobs.com/en-US/External"),
            ("Goldman Sachs", "https://goldmansachs.wd1.myworkdayjobs.com/en-US/External"),
            ("Barclays", "https://barclays.wd1.myworkdayjobs.com/en-US/External"),
            ("TCS", "https://tcs.wd3.myworkdayjobs.com/en-US/TCS_Careers"),
            ("Infosys", "https://infosys.wd1.myworkdayjobs.com/en-US/External"),
            ("Accenture", "https://accenture.wd1.myworkdayjobs.com/en-US/AccentureCareers"),
            ("Deloitte", "https://deloitte.wd1.myworkdayjobs.com/en-US/Deloitte"),
            ("PwC", "https://pwc.wd1.myworkdayjobs.com/en-US/External"),
            ("EY", "https://ey.wd1.myworkdayjobs.com/en-US/Careers"),
            ("KPMG", "https://kpmg.wd1.myworkdayjobs.com/en-US/External"),
        ]
    }
    
    all_jobs = []
    
    print(f"  [1/3] Greenhouse: {len(companies['greenhouse'])} companies")
    for company_name, company_id in companies['greenhouse']:
        jobs = collect_greenhouse(company_name, company_id)
        filtered = [j for j in jobs if is_relevant(j['title'], j['location'])]
        all_jobs.extend(filtered)
        print(f"    {company_name}: {len(filtered)} relevant")
    
    print(f"  [2/3] Lever: {len(companies['lever'])} companies")
    for company_name, company_id in companies['lever']:
        jobs = collect_lever(company_name, company_id)
        filtered = [j for j in jobs if is_relevant(j['title'], j['location'])]
        all_jobs.extend(filtered)
        print(f"    {company_name}: {len(filtered)} relevant")
    
    print(f"  [3/3] Workday: {len(companies['workday'])} companies")
    for company_name, company_url in companies['workday']:
        jobs = collect_workday(company_name, company_url)
        filtered = [j for j in jobs if is_relevant(j['title'], j['location'])]
        all_jobs.extend(filtered)
        print(f"    {company_name}: {len(filtered)} relevant")
    
    if all_jobs:
        save_jobs(all_jobs)
        compute_daily_skills()
        print(f"  Total new jobs: {len(all_jobs)}")
    else:
        print("  No new jobs found")
    
    print(f"[{datetime.now()}] ===== Collection Complete =====\n")

if __name__ == "__main__":
    print("Job Radar Collector Starting...")
    print("  Sources: Greenhouse, Lever, Workday")
    print("  Skills: DYNAMICALLY EXTRACTED using spaCy NLP\n")
    
    init_db()
    collect_all()
    
    print("Starting scheduler (every 6 hours)...")
    scheduler = BlockingScheduler()
    scheduler.add_job(collect_all, 'interval', hours=6)
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)
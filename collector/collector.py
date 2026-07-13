import psycopg2
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
import os
import time
import sys

from greenhouse import collect_greenhouse
from lever import collect_lever
from workday import collect_workday

DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'jobradar_db')
DB_USER = os.getenv('DB_USER', 'jobradar')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'jobradar123')

SKILLS = [
    'python', 'sql', 'pandas', 'numpy', 'scikit-learn', 'pytorch',
    'tensorflow', 'aws', 'docker', 'linux', 'git', 'powerbi',
    'tableau', 'spark', 'kafka', 'airflow', 'databricks',
    'postgresql', 'mongodb', 'fastapi', 'kubernetes', 'azure',
    'gcp', 'snowflake', 'mlflow', 'nlp', 'llm', 'rag', 'keras',
    'flask', 'django', 'hadoop', 'excel', 'scala', 'java',
    'c++', 'javascript', 'react', 'angular', 'nodejs',
    'mlops', 'dvc', 'prometheus', 'grafana'
]

ROLE_KEYWORDS = [
    'data scientist', 'data analyst', 'ml engineer',
    'machine learning engineer', 'data engineer', 'ai engineer',
    'research scientist', 'applied scientist', 'data architect'
]

LEVEL_KEYWORDS = [
    'intern', 'junior', 'associate', 'graduate', 'entry', 'fresher',
    'trainee', '0-2', '0-3', '0-1', 'early career', 'new grad'
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
        CREATE TABLE IF NOT EXISTS company_stats (
            company TEXT PRIMARY KEY,
            total_jobs INTEGER DEFAULT 0,
            last_seen DATE
        )
    """)
    
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_posted_date ON jobs(posted_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source)")
    
    conn.commit()
    cur.close()
    conn.close()
    print("  Database initialized")

def extract_skills(text):
    if not text:
        return []
    found = []
    text_lower = text.lower()
    for skill in SKILLS:
        if skill in text_lower:
            found.append(skill)
    return list(set(found))

def is_relevant(title, location):
    title_lower = title.lower()
    location_lower = location.lower()
    
    role_match = any(k in title_lower for k in ROLE_KEYWORDS)
    if not role_match:
        return False
    
    level_match = any(k in title_lower for k in LEVEL_KEYWORDS)
    if not level_match:
        return False
    
    location_match = any(k in location_lower for k in LOCATIONS)
    return location_match

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
    conn = get_db_connection()
    cur = conn.cursor()
    
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
    
    skill_counts = {}
    
    for job_id, title, description in jobs:
        text = f"{title} {description if description else ''}"
        skills = extract_skills(text)
        for skill in skills:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
    
    if not skill_counts:
        print("  No skills extracted")
        cur.close()
        conn.close()
        return
    
    sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
    
    for rank, (skill, count) in enumerate(sorted_skills, 1):
        cur.execute("""
            INSERT INTO skills_daily (date, skill, count, rank)
            VALUES (CURRENT_DATE, %s, %s, %s)
            ON CONFLICT (date, skill) DO UPDATE SET
                count = EXCLUDED.count,
                rank = EXCLUDED.rank
        """, (skill, count, rank))
        
        cur.execute("""
            INSERT INTO skills_trend (skill, date, count)
            VALUES (%s, CURRENT_DATE, %s)
            ON CONFLICT (skill, date) DO UPDATE SET
                count = EXCLUDED.count
        """, (skill, count))
    
    conn.commit()
    cur.close()
    conn.close()
    print(f"  Computed {len(sorted_skills)} skills")

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
            ("JPMorgan Chase", "jpmorgan"),
            ("Morgan Stanley", "morganstanley"),
            ("Goldman Sachs", "goldmansachs"),
            ("Barclays", "barclays"),
            ("NVIDIA", "nvidia"),
            ("Microsoft", "microsoft"),
            ("TCS", "tcs"),
            ("Infosys", "infosys"),
            ("Accenture", "accenture"),
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
    for company_name, company_id in companies['workday']:
        jobs = collect_workday(company_name, company_id)
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
    print("  Sources: Greenhouse, Lever, Workday\n")
    
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
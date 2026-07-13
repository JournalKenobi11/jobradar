import psycopg2
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
import os
import time
import sys
from huggingface_hub import snapshot_download
import spacy
from collections import Counter

from greenhouse import collect_greenhouse
from lever import collect_lever
from workday import collect_workday_public as collect_workday


# ============================================================
# LOGGING HELPERS
# ============================================================

def log(message="", level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}", flush=True)


def log_section(title):
    print("\n" + "=" * 70, flush=True)
    log(title)
    print("=" * 70, flush=True)


DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'jobradar_db')
DB_USER = os.getenv('DB_USER', 'jobradar')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'jobradar123')

# ============================================================
# LOAD SKILL EXTRACTION MODEL
# ============================================================

log_section("Loading Skill Extraction Model")

start = time.time()

log("Downloading model from Hugging Face cache/server...")

model_path = snapshot_download(
    repo_id="amjad-awad/skill-extractor",
    repo_type="model"
)

log(f"Model path: {model_path}")

log("Loading spaCy pipeline...")

nlp = spacy.load(model_path)

log(f"Model loaded successfully ({time.time() - start:.2f} sec)")

ROLE_KEYWORDS = [
    'data scientist', 'data analyst', 'ml engineer',
    'machine learning engineer', 'data engineer', 'ai engineer',
    'research scientist', 'applied scientist', 'data architect',
    'astrophysicist', 'astronomer', 'scientific programmer',
    'scientific computing', 'hpc', 'computational scientist'
]

LOCATIONS = [
    'mumbai', 'pune', 'bangalore', 'hyderabad', 'chennai',
    'delhi', 'gurgaon', 'noida', 'india', 'hybrid'
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
            log(
                 f"Database connection attempt "
                 f"{i + 1}/{max_retries} failed: {e}",
                 level="WARNING"
                )
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
    log("Database initialized successfully")

def is_relevant(title, location):
    title_lower = title.lower()
    location_lower = location.lower()
    
    role_match = any(k in title_lower for k in ROLE_KEYWORDS)
    if not role_match:
        return False
    
    location_match = any(k in location_lower for k in LOCATIONS)
    return location_match

def extract_skills_spacy(text):
    if not text or len(text) < 10:
        return []
    
    doc = nlp(text)
    skills = [ent.text for ent in doc.ents if "SKILL" in ent.label_]
    return list(set(skills))

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
            log(f"Error saving job: {e}", level="ERROR")
    
    conn.commit()
    cur.close()
    conn.close()
    log(f"Saved {saved_count} new jobs")

def compute_daily_skills():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT job_id, title, description FROM jobs
        WHERE posted_date = CURRENT_DATE
    """)
    
    jobs = cur.fetchall()
    
    if not jobs:
        log("No jobs collected today. Skipping skill computation.")
        cur.close()
        conn.close()
        return
    
    skill_counts = {}
    all_skill_terms = []
    
    for job_id, title, description in jobs:
        text = f"{title} {description if description else ''}"
        skills = extract_skills_spacy(text)
        all_skill_terms.extend(skills)
        for skill in skills:
            skill_counts[skill] = skill_counts.get(skill, 0) + 1
    
    if not skill_counts:
        log("No skills extracted from today's jobs.")
        cur.close()
        conn.close()
        return
    
    sorted_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)
    
    for rank, (skill, count) in enumerate(sorted_skills[:200], 1):
        cur.execute("""
            INSERT INTO skills_daily (date, skill, count, rank)
            VALUES (CURRENT_DATE, %s, %s, %s)
            ON CONFLICT (date, skill) DO UPDATE SET
                count = EXCLUDED.count,
                rank = EXCLUDED.rank
        """, (skill, count, rank))
    
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
    log(f"Computed {len(sorted_skills)} unique skills")

def collect_all():
    cycle_start = time.time()
    log_section("Starting Collection Cycle")
    
    # ============================================================
    # YOUR FULL COMPANY LIST - ADDED AS REQUESTED
    # ============================================================
    companies = {
        'greenhouse': [
            ("Razorpay", "razorpay"),
            ("Postman", "postman"),
            ("CRED", "cred"),
            ("Meesho", "meesho"),
            ("Swiggy", "swiggy"),
            ("Zepto", "zepto"),
            ("Groww", "groww"),
            ("PhonePe", "phonepe"),
            ("Flipkart", "flipkart"),
            ("Paytm", "paytm"),
            ("Zomato", "zomato"),
            ("Ola", "ola"),
            ("Dream11", "dream11"),
            ("Fractal Analytics", "fractal-analytics"),
            ("Quantiphi", "quantiphi"),
            ("Tiger Analytics", "tiger-analytics"),
            ("ZS Associates", "zs-associates"),
            ("Mu Sigma", "mu-sigma"),
            ("LatentView Analytics", "latentview"),
            ("NielsenIQ", "nielseniq"),
            ("Course5 Intelligence", "course5"),
            ("Stripe", "stripe"),
            ("Slack", "slack"),
            ("Shopify", "shopify"),
            ("Dropbox", "dropbox"),
            ("Pinterest", "pinterest"),
            ("Airbnb", "airbnb"),
            ("Uber", "uber"),
            ("Lyft", "lyft"),
            ("Reddit", "reddit"),
            ("Coinbase", "coinbase"),
            ("Robinhood", "robinhood"),
            ("Palantir", "palantir"),
        ],
        'lever': [
            ("Zerodha", "zerodha"),
            ("Groww", "groww"),
            ("CRED", "cred"),
            ("Meesho", "meesho"),
            ("Swiggy", "swiggy"),
            ("Zepto", "zepto"),
            ("Razorpay", "razorpay"),
            ("PhonePe", "phonepe"),
            ("Zomato", "zomato"),
            ("Ola", "ola"),
            ("Paytm", "paytm"),
            ("Flipkart", "flipkart"),
            ("Netflix", "netflix"),
            ("Spotify", "spotify"),
            ("Uber", "uber"),
            ("Lyft", "lyft"),
            ("Slack", "slack"),
            ("Shopify", "shopify"),
            ("Mozilla", "mozilla"),
            ("GitHub", "github"),
            ("GitLab", "gitlab"),
            ("Figma", "figma"),
            ("Vercel", "vercel"),
            ("Cloudflare", "cloudflare"),
            ("Weights & Biases", "wandb"),
            ("Hugging Face", "huggingface"),
            ("Modal Labs", "modal"),
            ("Replicate", "replicate"),
            ("Cerebras", "cerebras"),
        ],
        'workday': [
            ("NVIDIA", "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"),
            ("Microsoft", "https://microsoft.wd1.myworkdayjobs.com/en-US/MSFTJobs"),
            ("Amazon", "https://amazon.wd1.myworkdayjobs.com/en-US/External"),
            ("Google", "https://google.wd1.myworkdayjobs.com/en-US/GoogleExternal"),
            ("Apple", "https://apple.wd1.myworkdayjobs.com/en-US/External"),
            ("Meta", "https://meta.wd1.myworkdayjobs.com/en-US/MetaExternal"),
            ("AMD", "https://amd.wd1.myworkdayjobs.com/en-US/External"),
            ("Intel", "https://intel.wd1.myworkdayjobs.com/en-US/External"),
            ("Oracle", "https://oracle.wd1.myworkdayjobs.com/en-US/External"),
            ("Salesforce", "https://salesforce.wd1.myworkdayjobs.com/en-US/External_Career_Site"),
            ("TCS", "https://tcs.wd3.myworkdayjobs.com/en-US/TCS_Careers"),
            ("Infosys", "https://infosys.wd1.myworkdayjobs.com/en-US/External"),
            ("Wipro", "https://wipro.wd1.myworkdayjobs.com/en-US/External"),
            ("Accenture", "https://accenture.wd1.myworkdayjobs.com/en-US/AccentureCareers"),
            ("Capgemini", "https://capgemini.wd1.myworkdayjobs.com/en-US/External"),
            ("Cognizant", "https://cognizant.wd1.myworkdayjobs.com/en-US/External"),
            ("IBM", "https://ibm.wd1.myworkdayjobs.com/en-US/External"),
            ("Deloitte", "https://deloitte.wd1.myworkdayjobs.com/en-US/Deloitte"),
            ("PwC", "https://pwc.wd1.myworkdayjobs.com/en-US/External"),
            ("EY", "https://ey.wd1.myworkdayjobs.com/en-US/Careers"),
            ("KPMG", "https://kpmg.wd1.myworkdayjobs.com/en-US/External"),
            ("JPMorgan Chase", "https://jpmchase.wd1.myworkdayjobs.com/en-US/External"),
            ("Morgan Stanley", "https://morganstanley.wd1.myworkdayjobs.com/en-US/External"),
            ("Goldman Sachs", "https://goldmansachs.wd1.myworkdayjobs.com/en-US/External"),
            ("Barclays", "https://barclays.wd1.myworkdayjobs.com/en-US/External"),
            ("Deutsche Bank", "https://db.wd1.myworkdayjobs.com/en-US/External"),
            ("HSBC", "https://hsbc.wd1.myworkdayjobs.com/en-US/External"),
            ("Citigroup", "https://citi.wd1.myworkdayjobs.com/en-US/External"),
            ("Bank of America", "https://bankofamerica.wd1.myworkdayjobs.com/en-US/External"),
            ("Wells Fargo", "https://wellsfargo.wd1.myworkdayjobs.com/en-US/External"),
            ("Mastercard", "https://mastercard.wd1.myworkdayjobs.com/en-US/External"),
            ("Visa", "https://visa.wd1.myworkdayjobs.com/en-US/External"),
            ("Credit Suisse", "https://creditsuisse.wd1.myworkdayjobs.com/en-US/External"),
            ("UBS", "https://ubs.wd1.myworkdayjobs.com/en-US/External"),
            ("BNP Paribas", "https://bnpparibas.wd1.myworkdayjobs.com/en-US/External"),
            ("Societe Generale", "https://societegenerale.wd1.myworkdayjobs.com/en-US/External"),
            ("Nomura", "https://nomura.wd1.myworkdayjobs.com/en-US/External"),
            ("Mitsubishi UFJ", "https://mufg.wd1.myworkdayjobs.com/en-US/External"),
            ("Jane Street", "https://janestreet.wd1.myworkdayjobs.com/en-US/External"),
            ("Optiver", "https://optiver.wd1.myworkdayjobs.com/en-US/External"),
            ("Susquehanna", "https://sig.wd1.myworkdayjobs.com/en-US/External"),
            ("Jump Trading", "https://jumptrading.wd1.myworkdayjobs.com/en-US/External"),
            ("Citadel", "https://citadel.wd1.myworkdayjobs.com/en-US/External"),
            ("HDFC Bank", "https://hdfcbank.wd1.myworkdayjobs.com/en-US/External"),
            ("ICICI Bank", "https://icici.wd1.myworkdayjobs.com/en-US/External"),
            ("Axis Bank", "https://axisbank.wd1.myworkdayjobs.com/en-US/External"),
            ("SBI", "https://sbi.wd1.myworkdayjobs.com/en-US/External"),
        ]
    }
    
    all_jobs = []
    greenhouse_start = time.time()
    log(f"[1/3] Greenhouse ({len(companies['greenhouse'])} companies)")
    for company_name, company_id in companies['greenhouse']:
        jobs = collect_greenhouse(company_name, company_id)
        filtered = [j for j in jobs if is_relevant(j['title'], j['location'])]
        all_jobs.extend(filtered)

        log(f"    {company_name}: {len(filtered)} relevant")
    greenhouse_time = time.time() - greenhouse_start

    log(
    f"[GREENHOUSE] Completed | "
    f"Companies: {len(companies['greenhouse'])} | "
    f"Time: {greenhouse_time:.2f}s"
)
    lever_start = time.time()
    log(f"  [2/3] Lever: {len(companies['lever'])} companies")
    for company_name, company_id in companies['lever']:
        jobs = collect_lever(company_name, company_id)
        filtered = [j for j in jobs if is_relevant(j['title'], j['location'])]
        all_jobs.extend(filtered)
        log(f"    {company_name}: {len(filtered)} relevant")

    lever_time = time.time() - lever_start

    log(
    f"[LEVER] Completed | "
    f"Companies: {len(companies['lever'])} | "
    f"Time: {lever_time:.2f}s"
     )
    
    workday_start = time.time()
    log(f"  [3/3] Workday: {len(companies['workday'])} companies")
    for company_name, company_url in companies['workday']:
        jobs = collect_workday(company_name, company_url)
        filtered = [j for j in jobs if is_relevant(j['title'], j['location'])]
        all_jobs.extend(filtered)
        log(f"    {company_name}: {len(filtered)} relevant")
    
    workday_time = time.time() - workday_start

    log(
    f"[WORKDAY] Completed | "
    f"Companies: {len(companies['workday'])} | "
    f"Time: {workday_time:.2f}s"
     )

    if all_jobs:
        save_jobs(all_jobs)
        compute_daily_skills()
        log(f"  Total new jobs: {len(all_jobs)}")
    else:
        log("  No new jobs found in this cycle")
    
    log_section("Collection Cycle Complete")

if __name__ == "__main__":
    log_section("Job Radar Collector")

    log("Sources : Greenhouse, Lever, Workday")
    log("Skill Extractor : amjad-awad/skill-extractor")
    log(f"Database : {DB_HOST}:{DB_PORT}/{DB_NAME}")
    
    init_db()
    collect_all()
    
    log("Scheduler started (every 6 hours)")
    scheduler = BlockingScheduler()
    scheduler.add_job(collect_all, 'interval', hours=6)
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        log("Collector stopped", "INFO")
        sys.exit(0)
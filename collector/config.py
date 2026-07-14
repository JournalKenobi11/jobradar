"""Configuration Module.

This module acts as a single source of truth for all environment variables,
database configurations, keyword rules, and targeted scrape target lists.
"""

import os

# ============================================================
# DATABASE CREDENTIALS
# ============================================================
DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'jobradar_db')
DB_USER = os.getenv('DB_USER', 'jobradar')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'jobradar123')

# ============================================================
# FILTERING CRITERIA KEYWORDS
# ============================================================
# Role-related keywords used to check job title relevance
ROLE_KEYWORDS = [
    'data scientist', 'data analyst', 'ml engineer',
    'machine learning engineer', 'data engineer', 'ai engineer',
    'research scientist', 'applied scientist', 'data architect',
    'astrophysicist', 'astronomer', 'scientific programmer',
    'scientific computing', 'hpc', 'computational scientist'
]

# Target location keywords for geo-filtering
LOCATIONS = [
    'mumbai', 'pune', 'bangalore', 'hyderabad', 'chennai',
    'delhi', 'gurgaon', 'noida', 'india', 'hybrid'
]

# ============================================================
# SCRAPER TARGET REGISTRY
# ============================================================
COMPANIES = {
    'greenhouse': [
        ("Razorpay", "razorpay"), ("Postman", "postman"), ("CRED", "cred"),
        ("Meesho", "meesho"), ("Swiggy", "swiggy"), ("Zepto", "zepto"),
        ("Groww", "groww"), ("PhonePe", "phonepe"), ("Flipkart", "flipkart"),
        ("Paytm", "paytm"), ("Zomato", "zomato"), ("Ola", "ola"),
        ("Dream11", "dream11"), ("Fractal Analytics", "fractal-analytics"),
        ("Quantiphi", "quantiphi"), ("Tiger Analytics", "tiger-analytics"),
        ("ZS Associates", "zs-associates"), ("Mu Sigma", "mu-sigma"),
        ("LatentView Analytics", "latentview"), ("NielsenIQ", "nielseniq"),
        ("Course5 Intelligence", "course5"), ("Stripe", "stripe"),
        ("Slack", "slack"), ("Shopify", "shopify"), ("Dropbox", "dropbox"),
        ("Pinterest", "pinterest"), ("Airbnb", "airbnb"), ("Uber", "uber"),
        ("Lyft", "lyft"), ("Reddit", "reddit"), ("Coinbase", "coinbase"),
        ("Robinhood", "robinhood"), ("Palantir", "palantir"),
    ],
    'lever': [
        ("Zerodha", "zerodha"), ("Groww", "groww"), ("CRED", "cred"),
        ("Meesho", "meesho"), ("Swiggy", "swiggy"), ("Zepto", "zepto"),
        ("Razorpay", "razorpay"), ("PhonePe", "phonepe"), ("Zomato", "zomato"),
        ("Ola", "ola"), ("Paytm", "paytm"), ("Flipkart", "flipkart"),
        ("Netflix", "netflix"), ("Spotify", "spotify"), ("Uber", "uber"),
        ("Lyft", "lyft"), ("Slack", "slack"), ("Shopify", "shopify"),
        ("Mozilla", "mozilla"), ("GitHub", "github"), ("GitLab", "gitlab"),
        ("Figma", "figma"), ("Vercel", "vercel"), ("Cloudflare", "cloudflare"),
        ("Weights & Biases", "wandb"), ("Hugging Face", "huggingface"),
        ("Modal Labs", "modal"), ("Replicate", "replicate"), ("Cerebras", "cerebras"),
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
companies = {
    'greenhouse': [
        # Verified via resolver (real tokens, confirmed by non-404 responses)
        ("Razorpay", "razorpaysoftwareprivatelimited"),  # NOTE: was "razorpay" - wrong, fixed
        ("Postman", "postman"),
        ("Groww", "groww"),
        ("PhonePe", "phonepe"),
        ("Stripe", "stripe"),
        ("Dropbox", "dropbox"),
        ("Pinterest", "pinterest"),
        ("Airbnb", "airbnb"),
        ("Lyft", "lyft"),
        ("Reddit", "reddit"),
        ("Coinbase", "coinbase"),
        ("Robinhood", "robinhood"),
        ("Mozilla", "mozilla"),
        ("GitLab", "gitlab"),
        ("Figma", "figma"),
        ("Vercel", "vercel"),
        ("Cloudflare", "cloudflare"),
        ("TCS", "tcs"),
        ("Jane Street", "janestreet"),
        ("Optiver", "optiver"),
        ("Jump Trading", "jumptrading"),
    ],

    'lever': [
        # Verified via resolver
        ("CRED", "cred"),
        ("Meesho", "meesho"),
        ("Paytm", "paytm"),
        ("Palantir", "palantir"),
        ("Netflix", "netflix"),
        ("Spotify", "spotify"),
        ("KPMG", "kpmg"),
        ("Deloitte", "deloitte"),  # new find - spot-check once before fully trusting
    ],

    'smartrecruiters': [
        # Verified via resolver (now requires totalFound > 0, so these are real)
        ("Swiggy", "swiggy"),
        ("NielsenIQ", "nielseniq"),
        ("Uber", "uber"),
        ("Visa", "visa"),
    ],

    'workable': [
        # Verified via resolver (now requires jobs > 0, so these are real)
        ("Tiger Analytics", "tiger-analytics"),
        ("Hugging Face", "huggingface"),
    ],

    'recruitee': [
        # Verified via resolver (non-empty offers), but SANITY-CHECK MANUALLY
        # before trusting fully - unusual for companies this size to run
        # Recruitee. Open these URLs in a browser once:
        #   https://meta.recruitee.com/api/offers/
        #   https://salesforce.recruitee.com/api/offers/
        #   https://accenture.recruitee.com/api/offers/
        #   https://ey.recruitee.com/api/offers/
        ("Meta", "meta"),
        ("Salesforce", "salesforce"),
        ("Accenture", "accenture"),
        ("EY", "ey"),
    ],

    'workday': [
        # These were ALREADY CORRECT in your original list - the resolver's
        # crawl-based guesses for some of these (Citigroup, Bank of America,
        # Mastercard) were WRONG (grabbed random tracking/asset paths from
        # the page, not the real job board). Keeping your original, verified
        # URLs here unchanged. The only fix needed was in workday.py itself
        # (missing appliedFacets), which is already done.
        ("NVIDIA", "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"),
        ("Microsoft", "https://microsoft.wd1.myworkdayjobs.com/en-US/MSFTJobs"),
        ("Amazon", "https://amazon.wd1.myworkdayjobs.com/en-US/External"),
        ("Google", "https://google.wd1.myworkdayjobs.com/en-US/GoogleExternal"),
        ("Apple", "https://apple.wd1.myworkdayjobs.com/en-US/External"),
        ("Meta", "https://meta.wd1.myworkdayjobs.com/en-US/MetaExternal"),
        ("AMD", "https://amd.wd1.myworkdayjobs.com/en-US/External"),
        ("Intel", "https://intel.wd1.myworkdayjobs.com/en-US/External"),
        ("Oracle", "https://oracle.wd1.myworkdayjobs.com/en-US/External"),
        ("Salesforce", "https://salesforce.wd1.myworkdayjobs.com/en-US/External"),
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
    ],
}

# ---------------------------------------------------------------------------
# NO PUBLIC ATS FOUND - confirmed unresolved after direct-guess + site-crawl.
# These need either a custom scraper for their career page, or should be
# dropped from your target list. Not worth chasing for a handful of DS roles
# unless one of these is a must-have target for you.
# ---------------------------------------------------------------------------
NO_PUBLIC_ATS = [
    "Zepto", "Flipkart", "Zomato", "Ola", "Dream11",
    "ZS Associates", "Mu Sigma", "LatentView Analytics", "Course5 Intelligence",
    "GitHub", "Shopify", "Zerodha",
    "Weights & Biases", "Modal Labs", "Replicate", "Cerebras",
    # Susquehanna and Citadel are NOT in this list - they already have
    # working Workday URLs in the 'workday' section above.
]
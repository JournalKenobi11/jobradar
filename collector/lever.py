import requests
from datetime import datetime

def collect_lever(company_name, company_id):
    # Try Global first
    url = f"https://api.lever.co/v0/postings/{company_id}?mode=json"
    response = None
    is_eu = False
    
    try:
        response = requests.get(url, timeout=30)
        
        # If 404, try EU instance
        if response.status_code == 404:
            url = f"https://api.eu.lever.co/v0/postings/{company_id}?mode=json"
            response = requests.get(url, timeout=30)
            is_eu = True
        
        if response.status_code != 200:
            print(f"  [Lever] {company_name}: HTTP {response.status_code}")
            return []
        
        data = response.json()
        jobs = []
        
        for job in data:
            title = job.get('title', '')
            location = job.get('location', '')
            job_url = f"https://jobs.lever.co/{company_id}/{job.get('id', '')}"
            
            jobs.append({
                'job_id': f"lever_{company_id}_{job.get('id')}",
                'company': company_name,
                'title': title,
                'location': location if location else 'India',
                'description': job.get('description', '') or job.get('descriptionPlain', ''),
                'url': job_url,
                'source': 'lever',
                'posted_date': datetime.now().date()
            })
        
        region = "EU" if is_eu else "Global"
        print(f"  [Lever] {company_name} ({region}): Found {len(jobs)} jobs")
        return jobs
    except Exception as e:
        print(f"  [Lever] Error fetching {company_name}: {e}")
        return []
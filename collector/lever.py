import requests
from datetime import datetime

def collect_lever(company_name, company_id):
    url = f"https://api.lever.co/v0/postings/{company_id}"
    
    try:
        response = requests.get(url, timeout=15)
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
                'location': location,
                'description': job.get('description', ''),
                'url': job_url,
                'source': 'lever',
                'posted_date': datetime.now().date()
            })
        
        return jobs
    except Exception as e:
        print(f"  [Lever] Error fetching {company_name}: {e}")
        return []
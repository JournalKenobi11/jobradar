import requests
from datetime import datetime

def collect_greenhouse(company_name, company_id):
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs"
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            print(f"  [Greenhouse] {company_name}: HTTP {response.status_code}")
            return []
        
        data = response.json()
        jobs = []
        
        for job in data.get('jobs', []):
            title = job.get('title', '')
            location = job.get('location', {}).get('name', '')
            job_url = job.get('absolute_url', '')
            
            jobs.append({
                'job_id': f"greenhouse_{company_id}_{job.get('id')}",
                'company': company_name,
                'title': title,
                'location': location,
                'description': job.get('content', ''),
                'url': job_url,
                'source': 'greenhouse',
                'posted_date': datetime.now().date()
            })
        
        return jobs
    except Exception as e:
        print(f"  [Greenhouse] Error fetching {company_name}: {e}")
        return []
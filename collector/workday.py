import requests
from datetime import datetime
import re

def collect_workday_public(company_name, company_url):
    try:
        company_url = company_url.rstrip('/')
        
        match = re.search(r'https://([^.]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[^/]+)/([^/]+)', company_url)
        if not match:
            print(f"  [Workday] {company_name}: Could not parse URL")
            return []
        
        tenant = match.group(1)
        instance = match.group(2)
        site = match.group(3)
        
        api_url = f"https://{tenant}.{instance}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
        
        payload = {
            "limit": 50,
            "offset": 0,
            "searchText": ""
        }
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"  [Workday] {company_name}: HTTP {response.status_code}")
            return []
        
        data = response.json()
        job_list = data.get('jobPostings', data.get('items', []))
        
        if not job_list:
            print(f"  [Workday] {company_name}: No jobs found")
            return []
        
        jobs = []
        for job in job_list:
            title = job.get('title', job.get('jobTitle', ''))
            if not title:
                continue
            
            location = ''
            if 'location' in job:
                location = job.get('location', '')
            elif 'locations' in job and job['locations']:
                locations = job['locations']
                if isinstance(locations, list) and len(locations) > 0:
                    location = locations[0].get('city', '') or locations[0].get('country', '')
                elif isinstance(locations, dict):
                    location = locations.get('city', locations.get('country', ''))
            
            if not location:
                location = 'India'
            
            job_url = job.get('jobUrl', job.get('url', ''))
            if not job_url and job.get('id'):
                job_url = f"{company_url}/job/{job.get('id')}"
            
            description = job.get('description', job.get('jobDescription', ''))
            if isinstance(description, dict):
                description = description.get('text', '')
            
            job_id = job.get('id', job.get('requisitionId', ''))
            if not job_id:
                job_id = f"{company_name}_{title.replace(' ', '_')}"
            
            jobs.append({
                'job_id': f"workday_{company_name}_{job_id}",
                'company': company_name,
                'title': title,
                'location': str(location),
                'description': str(description),
                'url': str(job_url),
                'source': 'workday',
                'posted_date': datetime.now().date()
            })
        
        print(f"  [Workday] {company_name}: Found {len(jobs)} jobs")
        return jobs
        
    except Exception as e:
        print(f"  [Workday] Error fetching {company_name}: {e}")
        return []
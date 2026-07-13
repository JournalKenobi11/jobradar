import requests
from datetime import datetime
import re

def collect_workday_public(company_name, company_url):
    """
    Fetch jobs from public Workday career site using the CXS JSON API.
    No authentication required. Works with any public Workday career page.
    
    Args:
        company_name: Display name (e.g., "NVIDIA")
        company_url: Public career site URL
                    Example: https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite
    
    Returns:
        List of job dictionaries
    """
    try:
        # Clean the URL
        company_url = company_url.rstrip('/')
        
        # Construct the public API URL
        # Workday uses: {base_url}/jobs as the public JSON endpoint
        api_url = f"{company_url}/jobs"
        
        print(f"  [Workday] Fetching {company_name} from: {api_url}")
        
        # Headers that work with Workday's public API
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        response = requests.get(api_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"  [Workday] {company_name}: HTTP {response.status_code}")
            return []
        
        data = response.json()
        
        # Workday response structure variations
        # Some tenants use 'jobPostings', others use 'items'
        job_list = data.get('jobPostings', data.get('items', data.get('jobs', [])))
        
        if not job_list:
            print(f"  [Workday] {company_name}: No jobs found in response")
            return []
        
        jobs = []
        
        for job in job_list:
            # Extract title
            title = job.get('title', job.get('jobTitle', ''))
            if not title:
                continue
            
            # Extract location
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
            
            # Extract job URL
            job_url = job.get('jobUrl', job.get('url', ''))
            if not job_url and job.get('id'):
                job_url = f"{company_url}/job/{job.get('id')}"
            
            # Extract description
            description = job.get('description', job.get('jobDescription', ''))
            if isinstance(description, dict):
                description = description.get('text', '')
            
            # Extract job ID
            job_id = job.get('id', job.get('requisitionId', job.get('jobId', '')))
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
        
    except requests.exceptions.Timeout:
        print(f"  [Workday] Timeout fetching {company_name}")
        return []
    except requests.exceptions.JSONDecodeError:
        print(f"  [Workday] {company_name}: Invalid JSON response")
        return []
    except Exception as e:
        print(f"  [Workday] Error fetching {company_name}: {e}")
        return []


def collect_workday_with_search(company_name, company_url, keyword=""):
    """
    Fetch Workday jobs with search filter.
    Useful for narrowing down by title/role.
    """
    try:
        company_url = company_url.rstrip('/')
        
        # Add search parameter if provided
        if keyword:
            api_url = f"{company_url}/jobs?q={keyword}"
        else:
            api_url = f"{company_url}/jobs"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(api_url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return []
        
        data = response.json()
        job_list = data.get('jobPostings', data.get('items', data.get('jobs', [])))
        
        jobs = []
        for job in job_list:
            jobs.append({
                'job_id': f"workday_{company_name}_{job.get('id', '')}",
                'company': company_name,
                'title': job.get('title', ''),
                'location': job.get('location', 'India'),
                'description': job.get('description', ''),
                'url': job.get('jobUrl', ''),
                'source': 'workday',
                'posted_date': datetime.now().date()
            })
        
        return jobs
    except Exception as e:
        print(f"  [Workday] Search error for {company_name}: {e}")
        return []
import requests
from datetime import datetime

def collect_recruitee(company_name, company_id):
    url = f"https://{company_id}.recruitee.com/api/offers/"

    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            print(f"  [Recruitee] {company_name}: HTTP {response.status_code}")
            return []

        data = response.json()
        offers = data.get('offers', [])
        jobs = []

        for job in offers:
            title = job.get('title', '')

            city = job.get('city', '')
            country = job.get('country', '') or job.get('country_code', '')
            remote = job.get('remote', False)
            if remote and not city:
                loc_str = 'Remote'
            else:
                loc_str = ', '.join(filter(None, [city, country])) or 'India'

            job_id = job.get('id', job.get('slug', ''))
            job_url = job.get('careers_url', '') or \
                f"https://{company_id}.recruitee.com/o/{job.get('slug', job_id)}"

            jobs.append({
                'job_id': f"recruitee_{company_id}_{job_id}",
                'company': company_name,
                'title': title,
                'location': loc_str,
                'description': job.get('description', ''),
                'url': job_url,
                'source': 'recruitee',
                'posted_date': datetime.now().date()
            })

        print(f"  [Recruitee] {company_name}: Found {len(jobs)} jobs")
        return jobs
    except Exception as e:
        print(f"  [Recruitee] Error fetching {company_name}: {e}")
        return []
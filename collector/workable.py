import requests
from datetime import datetime

def collect_workable(company_name, company_id):
    url = f"https://apply.workable.com/api/v1/widget/accounts/{company_id}"

    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            print(f"  [Workable] {company_name}: HTTP {response.status_code}")
            return []

        data = response.json()
        job_list = data.get('jobs', [])
        jobs = []

        for job in job_list:
            title = job.get('title', '')

            location = job.get('location', {}) or {}
            loc_str = location.get('location_str', '')
            if not loc_str:
                city = location.get('city', '')
                country = location.get('country', '')
                loc_str = ', '.join(filter(None, [city, country]))
            if not loc_str:
                loc_str = 'India'

            shortcode = job.get('shortcode', job.get('id', ''))
            job_url = job.get('url', '') or job.get('shortlink', '') or \
                f"https://apply.workable.com/{company_id}/j/{shortcode}"

            jobs.append({
                'job_id': f"workable_{company_id}_{shortcode}",
                'company': company_name,
                'title': title,
                'location': loc_str,
                # Workable's public widget endpoint doesn't include full job
                # descriptions - only the account-level (authenticated) API
                # does. Leave blank rather than guessing.
                'description': job.get('description', ''),
                'url': job_url,
                'source': 'workable',
                'posted_date': datetime.now().date()
            })

        print(f"  [Workable] {company_name}: Found {len(jobs)} jobs")
        return jobs
    except Exception as e:
        print(f"  [Workable] Error fetching {company_name}: {e}")
        return []
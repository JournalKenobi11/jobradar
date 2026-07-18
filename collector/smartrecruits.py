import requests
from datetime import datetime

def collect_smartrecruiters(company_name, company_id):
    url = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings"

    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            print(f"  [SmartRecruiters] {company_name}: HTTP {response.status_code}")
            return []

        data = response.json()

        # Same trap as during resolution: a 200 with totalFound:0 does NOT
        # mean there are no jobs necessarily wrong company - but it can also
        # legitimately mean zero open roles right now. Either way, nothing
        # to collect, so just return empty rather than erroring.
        postings = data.get('content', [])
        jobs = []

        for job in postings:
            title = job.get('name', '')

            location = job.get('location', {}) or {}
            city = location.get('city', '')
            country = location.get('country', '')
            loc_str = ', '.join(filter(None, [city, country])) or 'India'

            job_id = job.get('id', job.get('uuid', ''))
            # SmartRecruiters public postings don't reliably include a direct
            # apply URL in this endpoint - build the standard public job page.
            job_url = job.get('postingUrl') or job.get('applyUrl') or \
                f"https://jobs.smartrecruiters.com/{company_id}/{job_id}"

            description = ''
            job_ad = job.get('jobAd', {})
            if isinstance(job_ad, dict):
                sections = job_ad.get('sections', {})
                if isinstance(sections, dict):
                    description = ' '.join(
                        str(v.get('text', '')) for v in sections.values() if isinstance(v, dict)
                    )
            if not description:
                description = job.get('description', '')

            jobs.append({
                'job_id': f"smartrecruiters_{company_id}_{job_id}",
                'company': company_name,
                'title': title,
                'location': loc_str,
                'description': description,
                'url': job_url,
                'source': 'smartrecruiters',
                'posted_date': datetime.now().date()
            })

        print(f"  [SmartRecruiters] {company_name}: Found {len(jobs)} jobs")
        return jobs
    except Exception as e:
        print(f"  [SmartRecruiters] Error fetching {company_name}: {e}")
        return []
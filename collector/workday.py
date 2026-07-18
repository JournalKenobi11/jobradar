import requests
from datetime import datetime
import re
import time

# Workday's CXS API rejects requests without "appliedFacets" (even empty) with a
# 400/422, and silently caps page size — asking for more than ~20 per page gets
# rejected or truncated by some tenants. This version fixes both, adds the
# headers some tenants require, and paginates until all jobs are collected.

PAGE_LIMIT = 20


def collect_workday_public(company_name, company_url, max_pages=25, pause_seconds=0.5):
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

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Accept-Language': 'en-US',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            # Some tenants reject requests without a matching Referer
            'Referer': f"https://{tenant}.{instance}.myworkdayjobs.com/en-US/{site}",
        }

        all_postings = []
        offset = 0
        total = None

        for page in range(max_pages):
            payload = {
                "appliedFacets": {},   # required — omitting this causes 400/422
                "limit": PAGE_LIMIT,
                "offset": offset,
                "searchText": ""
            }

            response = requests.post(api_url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                if page == 0:
                    print(f"  [Workday] {company_name}: HTTP {response.status_code}")
                    return []
                else:
                    # Failed mid-pagination — retry once rather than silently
                    # truncating the result set.
                    time.sleep(1)
                    retry = requests.post(api_url, headers=headers, json=payload, timeout=30)
                    if retry.status_code != 200:
                        print(f"  [Workday] {company_name}: page {page} failed (HTTP {retry.status_code}), stopping")
                        break
                    response = retry

            data = response.json()
            if total is None:
                total = data.get('total', 0)

            job_list = data.get('jobPostings', data.get('items', []))
            if not job_list:
                break

            all_postings.extend(job_list)
            offset += PAGE_LIMIT

            if total and offset >= total:
                break

            time.sleep(pause_seconds)  # be polite / avoid throttling

        if not all_postings:
            print(f"  [Workday] {company_name}: No jobs found")
            return []

        jobs = []
        for job in all_postings:
            title = job.get('title', job.get('jobTitle', ''))
            if not title:
                continue

            location = ''
            if 'locationsText' in job and job['locationsText']:
                location = job['locationsText']
            elif 'location' in job:
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
            external_path = job.get('externalPath', '')
            if not job_url and external_path:
                job_url = f"https://{tenant}.{instance}.myworkdayjobs.com/en-US/{site}{external_path}"
            elif not job_url and job.get('id'):
                job_url = f"{company_url}/job/{job.get('id')}"

            description = job.get('description', job.get('jobDescription', ''))
            if isinstance(description, dict):
                description = description.get('text', '')

            job_id = job.get('id', job.get('requisitionId', external_path or ''))
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
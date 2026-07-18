"""Job Radar Collector Orchestrator.

Acts as the pipeline controller. Sequentially pulls ATS integrations,
filters outputs, saves to the database layer, and triggers the analyzer engine.
"""

import sys
import time
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

# Custom project module imports
import config
import database
import filters
import nlp_engine

# Custom ATS integrations
from greenhouse import collect_greenhouse
from lever import collect_lever
from workday import collect_workday_public as collect_workday
from smartrecruiters import collect_smartrecruiters
from workable import collect_workable
from recruitee import collect_recruitee

# ============================================================
# ATS ADAPTER REGISTRY
# ============================================================
# Each entry: (display_name, config key in config.COMPANIES, collector fn)
# Adding a new ATS integration means adding one line here - not a new
# copy-pasted block.

ATS_ADAPTERS = [
    ("GREENHOUSE", "greenhouse", collect_greenhouse),
    ("LEVER", "lever", collect_lever),
    ("WORKDAY", "workday", collect_workday),
    ("SMARTRECRUITERS", "smartrecruiters", collect_smartrecruiters),
    ("WORKABLE", "workable", collect_workable),
    ("RECRUITEE", "recruitee", collect_recruitee),
]

# ============================================================
# PIPELINE DIAGNOSTIC LOGGING
# ============================================================

def log(message="", level="INFO"):
    """Global print formatter with standard dates and logging severity level tags."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}", flush=True)


def log_section(title):
    """Prints diagnostic rule breaks to partition scraping logic visually."""
    print("\n" + "=" * 70, flush=True)
    log(title)
    print("=" * 70, flush=True)


def run_platform(display_name, config_key, collector_fn, step, total_steps):
    """Runs one ATS adapter over all its configured companies.

    Returns (jobs_collected, fetched_count, relevant_count, rejected_count).
    """
    companies = config.COMPANIES.get(config_key, [])

    fetched_total = 0
    relevant_total = 0
    rejected_total = 0
    collected_jobs = []

    log(f"[{step}/{total_steps}] Processing {display_name.title()} APIs ({len(companies)} companies)")

    for company_name, company_id in companies:
        jobs = collector_fn(company_name, company_id)
        filtered = [j for j in jobs if filters.is_relevant(j['title'], j['location'])]
        collected_jobs.extend(filtered)

        fetched = len(jobs)
        relevant = len(filtered)
        rejected = fetched - relevant

        fetched_total += fetched
        relevant_total += relevant
        rejected_total += rejected

        log(f"[{display_name}] {company_name} -> Found {fetched} (Kept {relevant}, Rejected {rejected})")

    return collected_jobs, fetched_total, relevant_total, rejected_total


def run_collection_cycle():
    """Main Orchestration Loop.

    Iterates over every registered ATS adapter, filters jobs for relevance,
    records diagnostic summary statistics, and saves records.
    """
    cycle_start = time.time()
    log_section("Starting Collection Cycle")

    all_jobs = []
    total_steps = len(ATS_ADAPTERS)

    for step, (display_name, config_key, collector_fn) in enumerate(ATS_ADAPTERS, start=1):
        platform_start = time.time()

        jobs, fetched, relevant, rejected = run_platform(
            display_name, config_key, collector_fn, step, total_steps
        )
        all_jobs.extend(jobs)

        platform_time = time.time() - platform_start
        log_section(f"{display_name} CYCLE SUMMARY")
        log(f"Fetched   : {fetched} jobs")
        log(f"Relevant  : {relevant} jobs")
        log(f"Rejected  : {rejected} jobs")
        log(f"Time Taken: {platform_time:.2f} sec")

    # --------------------------------------------------------
    # PIPELINE INTEGRATION STEP
    # --------------------------------------------------------
    if all_jobs:
        database.save_jobs(all_jobs)
        nlp_engine.compute_daily_skills()
        log(f"Successfully pipeline-processed {len(all_jobs)} jobs.")
    else:
        log("Pipeline complete: No new relevant jobs discovered.")

    log_section(f"All runs completed in {time.time() - cycle_start:.2f} sec")


if __name__ == "__main__":
    log_section("Job Radar Pipeline Initialization Setup")

    active_adapters = ", ".join(name.title() for name, _, _ in ATS_ADAPTERS)
    log(f"Active Ingestion Adapters: {active_adapters}")
    log(f"Target Database Host: {config.DB_HOST}")

    # Ensure Database structures are active
    database.init_db()

    # Fire initial diagnostic cycle run instantly
    run_collection_cycle()

    # Build and initialize Cron Schedules (every 6 hours)
    log("Starting scheduling loops. Run interval set for 6 hours...")
    scheduler = BlockingScheduler()
    scheduler.add_job(run_collection_cycle, 'interval', hours=6)

    try:
        scheduler.start()
    except KeyboardInterrupt:
        log("Collector stopped gracefully.", "INFO")
        sys.exit(0)
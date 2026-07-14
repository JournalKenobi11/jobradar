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


def run_collection_cycle():
    """Main Orchestration Loop.

    Iterates over Greenhouse, Lever, and Workday APIs, filters jobs for
    relevance, records diagnostic summary statistics, and saves records.
    """
    cycle_start = time.time()
    log_section("Starting Collection Cycle")
    
    all_jobs = []

    # --------------------------------------------------------
    # SECTION 1: GREENHOUSE
    # --------------------------------------------------------
    greenhouse_fetched = 0
    greenhouse_relevant = 0
    greenhouse_rejected = 0
    greenhouse_start = time.time()

    log(f"[1/3] Processing Greenhouse APIs ({len(config.COMPANIES['greenhouse'])} companies)")

    for company_name, company_id in config.COMPANIES['greenhouse']:
        jobs = collect_greenhouse(company_name, company_id)
        filtered = [j for j in jobs if filters.is_relevant(j['title'], j['location'])]
        all_jobs.extend(filtered)

        fetched = len(jobs)
        relevant = len(filtered)
        rejected = fetched - relevant

        greenhouse_fetched += fetched
        greenhouse_relevant += relevant
        greenhouse_rejected += rejected

        log(f"[GREENHOUSE] {company_name} -> Found {fetched} (Kept {relevant}, Rejected {rejected})")

    greenhouse_time = time.time() - greenhouse_start
    log_section("GREENHOUSE CYCLE SUMMARY")
    log(f"Fetched   : {greenhouse_fetched} jobs")
    log(f"Relevant  : {greenhouse_relevant} jobs")
    log(f"Time Taken: {greenhouse_time:.2f} sec")

    # --------------------------------------------------------
    # SECTION 2: LEVER
    # --------------------------------------------------------
    lever_fetched = 0
    lever_relevant = 0
    lever_rejected = 0
    lever_start = time.time()

    log(f"[2/3] Processing Lever APIs ({len(config.COMPANIES['lever'])} companies)")

    for company_name, company_id in config.COMPANIES['lever']:
        jobs = collect_lever(company_name, company_id)
        filtered = [j for j in jobs if filters.is_relevant(j['title'], j['location'])]
        all_jobs.extend(filtered)

        fetched = len(jobs)
        relevant = len(filtered)
        rejected = fetched - relevant

        lever_fetched += fetched
        lever_relevant += relevant
        lever_rejected += rejected

        log(f"[LEVER] {company_name} -> Found {fetched} (Kept {relevant}, Rejected {rejected})")

    lever_time = time.time() - lever_start
    log_section("LEVER CYCLE SUMMARY")
    log(f"Fetched   : {lever_fetched} jobs")
    log(f"Relevant  : {lever_relevant} jobs")
    log(f"Time Taken: {lever_time:.2f} sec")

    # --------------------------------------------------------
    # SECTION 3: WORKDAY
    # --------------------------------------------------------
    workday_fetched = 0
    workday_relevant = 0
    workday_rejected = 0
    workday_start = time.time()

    log(f"[3/3] Processing Workday Integrations ({len(config.COMPANIES['workday'])} companies)")

    for company_name, company_url in config.COMPANIES['workday']:
        jobs = collect_workday(company_name, company_url)
        filtered = [j for j in jobs if filters.is_relevant(j['title'], j['location'])]
        all_jobs.extend(filtered)

        fetched = len(jobs)
        relevant = len(filtered)
        rejected = fetched - relevant

        workday_fetched += fetched
        workday_relevant += relevant
        workday_rejected += rejected

        log(f"[WORKDAY] {company_name} -> Found {fetched} (Kept {relevant}, Rejected {rejected})")

    workday_time = time.time() - workday_start
    log_section("WORKDAY CYCLE SUMMARY")
    log(f"Fetched   : {workday_fetched} jobs")
    log(f"Relevant  : {workday_relevant} jobs")
    log(f"Time Taken: {workday_time:.2f} sec")

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

    log("Active Ingestion Adapters: Greenhouse, Lever, Workday")
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
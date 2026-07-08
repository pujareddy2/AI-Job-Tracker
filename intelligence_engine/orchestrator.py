import json
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from intelligence_engine.company_registry import CompanyRegistry, CompanyProfile
from intelligence_engine.source_intelligence import SourceIntelligence, SourceCategory
from intelligence_engine.search_intelligence import SearchIntelligence
from intelligence_engine.retrieval_strategy import RetrievalStrategy
from intelligence_engine.verifier import Verifier
from job_model.universal_model import UniversalJobModel
from utils.logger import get_logger
from config import settings

logger = get_logger(__name__)

class JobIntelligenceEngine:
    """
    Main orchestrator for the new Job Discovery Architecture.
    """

    def __init__(self):
        self.company_registry = CompanyRegistry()
        self.source_health = SourceIntelligence()
        self.jobs_discovered: List[UniversalJobModel] = []

    def seed_companies_if_empty(self) -> None:
        """Seed the registry with a few companies if empty (e.g. initial run)."""
        if not self.company_registry.get_all():
            logger.info("Company registry is empty. Seeding defaults...")
            self.company_registry.add_or_update(CompanyProfile("Google", industry="Tech", hiring_platform="Greenhouse", career_url="https://careers.google.com"))
            self.company_registry.add_or_update(CompanyProfile("OpenAI", industry="AI", hiring_platform="Lever", career_url="https://openai.com/careers"))
            self.company_registry.add_or_update(CompanyProfile("Anthropic", industry="AI", hiring_platform="Workday", career_url="https://anthropic.com/careers"))
            self.company_registry.add_or_update(CompanyProfile("Scale AI", industry="AI", hiring_platform="Lever", career_url="https://scale.com/careers"))

    def _process_company(self, company: CompanyProfile, expanded_queries: List[str], location: str) -> List[UniversalJobModel]:
        """
        Processes a single company to find jobs.
        """
        logger.info(f"Processing company: {company.name}")
        
        # 1. Identify Adapter via RetrievalStrategy
        adapter = RetrievalStrategy.get_adapter(company.hiring_platform)
        
        # 2. Retrieve jobs with telemetry
        results = adapter.execute_with_telemetry(
            company.name, 
            company.career_url, 
            expanded_queries, 
            location, 
            self.source_health
        )
        
        valid_jobs = []
        for job in results:
            # 3. Verify Official Link
            if Verifier.verify_official_link(job.application.application_url, check_live=False):
                valid_jobs.append(job)
            else:
                logger.debug(f"Dropped job {job.job.job_title} due to failed URL verification.")
        
        # 4. Update Company Registry Health
        if valid_jobs:
            self.company_registry.record_success(company.name, len(valid_jobs))
        else:
            self.company_registry.record_failure(company.name, "No valid jobs found.")

        return valid_jobs

    def run_discovery(self, base_role: str, location: str) -> List[UniversalJobModel]:
        """
        Executes the intelligent discovery pipeline.
        """
        self.seed_companies_if_empty()
        
        # Phase 1: Search Intelligence Expansion
        expanded_queries = SearchIntelligence.expand_query(base_role, target_levels=False)
        logger.info(f"Expanded search queries to {len(expanded_queries)} variations.")

        companies = self.company_registry.get_all()
        logger.info(f"Starting discovery across {len(companies)} companies.")

        # Phase 2: Concurrent Collection
        all_jobs = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {
                executor.submit(self._process_company, company, expanded_queries, location): company 
                for company in companies 
                if company.status != "Degraded"
            }
            
            for future in as_completed(futures):
                company = futures[future]
                try:
                    jobs = future.result()
                    all_jobs.extend(jobs)
                except Exception as exc:
                    logger.error(f"Critical error processing company {company.name}: {exc}")

        # Final tracking and reporting
        self.jobs_discovered = all_jobs
        logger.info(f"Discovery complete. Found {len(all_jobs)} verified jobs.")
        
        # Output Discovery Report
        report = self.source_health.generate_discovery_report()
        logger.info(f"\n{report}")
        
        # For visualization in console
        print(report)
        
        return all_jobs

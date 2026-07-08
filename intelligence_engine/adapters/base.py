import time
import abc
import traceback
from typing import List, Dict, Any, Optional
from job_model.universal_model import UniversalJobModel
from utils.logger import get_logger

logger = get_logger(__name__)

class BaseAdapter(abc.ABC):
    """Base class for all retrieval methods (API, ATS, HTML, etc.)."""
    
    def __init__(self, source_name: str, source_category: str):
        self.source_name = source_name
        self.source_category = source_category

    @abc.abstractmethod
    def retrieve(self, company_name: str, base_url: str, keywords: List[str], location: str) -> List[UniversalJobModel]:
        """
        Retrieves jobs from the source, normalizes them into UniversalJobModel, and returns them.
        Should return an empty list on logical failure, raising exception only on fatal errors.
        """
        pass

    def execute_with_telemetry(self, company_name: str, base_url: str, keywords: List[str], location: str, health_tracker: Any) -> List[UniversalJobModel]:
        """
        Executes the retrieval logic while automatically tracking telemetry and health metrics.
        """
        logger.info(f"[{self.source_name}] Starting retrieval via {self.__class__.__name__} for {company_name}")
        health_tracker.record_attempt(self.source_name)
        
        start_time = time.time()
        try:
            results = self.retrieve(company_name, base_url, keywords, location)
            duration = time.time() - start_time
            
            # Record success (using placeholder numbers for accepted/rejected until filter stage)
            health_tracker.record_success(self.source_name, len(results), len(results), 0, duration)
            logger.info(f"[{self.source_name}] Successfully retrieved {len(results)} jobs in {duration:.2f}s")
            return results
            
        except Exception as exc:
            duration = time.time() - start_time
            err_msg = f"{type(exc).__name__}: {str(exc)}"
            logger.warning(f"[{self.source_name}] Failed after {duration:.2f}s - {err_msg}")
            health_tracker.record_failure(self.source_name, err_msg)
            return []

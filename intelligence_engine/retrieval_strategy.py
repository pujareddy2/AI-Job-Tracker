from typing import Dict, Type
from intelligence_engine.adapters.base import BaseAdapter
from intelligence_engine.adapters.ats_greenhouse import GreenhouseAdapter
from intelligence_engine.adapters.ats_lever import LeverAdapter
from intelligence_engine.adapters.ats_workday import WorkdayAdapter
from utils.logger import get_logger

logger = get_logger(__name__)

class RetrievalStrategy:
    """Maps a source or hiring platform to the appropriate adapter."""
    
    # Priority mapping for platforms
    PLATFORM_MAP: Dict[str, Type[BaseAdapter]] = {
        "Greenhouse": GreenhouseAdapter,
        "Lever": LeverAdapter,
        "Workday": WorkdayAdapter
    }

    @staticmethod
    def get_adapter(hiring_platform: str) -> BaseAdapter:
        """
        Returns the appropriate adapter instance for the given platform.
        Defaults to a generic ATS adapter or search discovery if unknown.
        """
        for key, adapter_class in RetrievalStrategy.PLATFORM_MAP.items():
            if key.lower() in hiring_platform.lower():
                logger.debug(f"Mapped {hiring_platform} to {adapter_class.__name__}")
                return adapter_class()
        
        # Fallback to a Generic Search Adapter (which we can implement later)
        # For now, just return a dummy adapter or log it
        logger.debug(f"No specific adapter found for {hiring_platform}. Using generic fallback.")
        # Returning LeverAdapter as a generic mock fallback for now until all 12 are built
        return LeverAdapter()

"""Optimized detector execution management."""
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any
import multiprocessing
from functools import lru_cache

from garak import _config
from garak.attempt import Attempt

class DetectorManager:
    """Manages optimized execution of detectors."""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or max(1, multiprocessing.cpu_count() - 1)
        self._detectors = {}
        self._result_cache = {}
    
    @lru_cache(maxsize=1000)
    def _get_detector(self, detector_name: str):
        """Get or load detector with caching."""
        if detector_name not in self._detectors:
            self._detectors[detector_name] = self._load_detector(detector_name)
        return self._detectors[detector_name]
    
    def _load_detector(self, detector_name: str):
        """Load detector plugin."""
        import garak._plugins
        return garak._plugins.load_plugin(f"detectors.{detector_name}")
    
    def detect_batch(self, attempts: List[Attempt], detector_name: str) -> List[Any]:
        """Process a batch of attempts through a detector in parallel."""
        detector = self._get_detector(detector_name)
        results = []
        
        # Use thread pool for parallel detection
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_results = []
            
            # Submit detection tasks
            for attempt in attempts:
                # Check cache first
                cache_key = f"{detector_name}:{hash(str(attempt.prompt))}"
                if cache_key in self._result_cache:
                    results.append(self._result_cache[cache_key])
                    continue
                    
                future = executor.submit(detector.detect, attempt)
                future_results.append((future, cache_key, attempt))
            
            # Collect results
            for future, cache_key, attempt in future_results:
                try:
                    result = future.result(timeout=getattr(_config.system, 'detect_timeout', 30))
                    self._result_cache[cache_key] = result
                    results.append(result)
                except Exception as e:
                    logging.error(f"Detection error for {attempt.prompt}: {e}")
                    results.append(None)
        
        return results

_detector_manager = None

def get_detector_manager() -> DetectorManager:
    """Get or create the global detector manager instance."""
    global _detector_manager
    if _detector_manager is None:
        _detector_manager = DetectorManager()
    return _detector_manager
"""Manages probe execution and optimization."""
import logging
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Type

from garak import _config
from garak.probes.base import Probe
from garak.attempt import Attempt

class ProbeExecutionManager:
    """Manages optimized execution of probes."""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or max(1, multiprocessing.cpu_count() - 1)
        
    def execute_probes(self, probes: List[Type[Probe]], generator) -> Dict[str, List[Attempt]]:
        """Execute probes in parallel with optimized resource usage."""
        results = {}
        
        # Group probes by parallelization capability
        parallel_probes = []
        sequential_probes = []
        
        for probe_cls in probes:
            if getattr(probe_cls, 'parallelisable_attempts', False):
                parallel_probes.append(probe_cls)
            else:
                sequential_probes.append(probe_cls)
        
        # Execute parallel probes
        if parallel_probes:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for probe_cls in parallel_probes:
                    probe = probe_cls(_config)
                    futures.append(executor.submit(probe.probe, generator))
                
                for future in as_completed(futures):
                    try:
                        probe_results = future.result()
                        results[probe_cls.__name__] = probe_results
                    except Exception as e:
                        logging.error(f"Error executing probe {probe_cls.__name__}: {e}")
        
        # Execute sequential probes
        for probe_cls in sequential_probes:
            try:
                probe = probe_cls(_config)
                results[probe_cls.__name__] = probe.probe(generator)
            except Exception as e:
                logging.error(f"Error executing probe {probe_cls.__name__}: {e}")
        
        return results
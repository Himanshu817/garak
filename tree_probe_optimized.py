"""Optimized tree traversal probe implementation."""
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Set
import json

from tqdm import tqdm

from garak import _config
from garak.probes.base import TreeSearchProbe

class OptimizedTreeSearchProbe(TreeSearchProbe):
    """TreeSearchProbe with optimized traversal and caching."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.term_cache: Dict[str, List[str]] = {}
        self.node_result_cache: Dict[str, List[float]] = {}
        self.pruned_paths: Set[str] = set()
        
        # Initialize pruning strategy
        from garak.probes.pruning import get_pruning_strategy
        self.pruning = get_pruning_strategy(
            strategy_name=getattr(_config.system, 'pruning_strategy', 'adaptive'),
            initial_threshold=getattr(_config.system, 'initial_prune_threshold', 0.5)
        )
        
        # Initialize result store for memory-mapped file storage
        from garak.memory_utils import get_result_store
        self.result_store = get_result_store(_config.transient.reportfile.name + '.mmap')
    
    def _should_explore_node(self, node_id: str, parent_score: float) -> bool:
        """Determine if a node should be explored using advanced pruning."""
        if node_id in self.pruned_paths:
            return False
            
        # Check if we should prune based on memory usage
        from garak.memory_utils import get_memory_monitor, cleanup_if_needed
        if get_memory_monitor().should_cleanup():
            cleanup_if_needed()
            
        # Use pruning strategy to make decision
        should_prune = self.pruning.should_prune(
            node_id, 
            parent_score,
            {'threshold': self.per_node_threshold}
        )
        
        if should_prune:
            self.pruned_paths.add(node_id)
            return False
            
        return True
    
    def _process_node_batch(self, nodes: List, detector) -> List:
        """Process a batch of nodes in parallel."""
        attempts_todo = []
        surface_forms = set()
        
        # Gather all prompts for the batch
        for node in nodes:
            node_terms = self._get_node_terms(node)
            for term in node_terms:
                if term not in surface_forms and term not in self.never_queue_forms:
                    surface_forms.add(term)
                    attempts_todo.extend(self._mint_attempt(p) for p in self._gen_prompts(term))
        
        # Execute attempts in optimized batches
        chunk_size = getattr(_config.system, 'probe_chunk_size', 5)
        with ThreadPoolExecutor() as executor:
            attempt_chunks = [attempts_todo[i:i+chunk_size] 
                            for i in range(0, len(attempts_todo), chunk_size)]
            futures = [executor.submit(self._execute_all, chunk) for chunk in attempt_chunks]
            completed_attempts = []
            for future in futures:
                completed_attempts.extend(future.result())
        
        return completed_attempts
    
    def probe(self, generator):
        """Optimized tree traversal with parallel processing and caching."""
        self.generator = generator
        detector = self._load_detector()
        
        initial_nodes = list(self._get_initial_nodes())
        if not initial_nodes:
            return []
            
        all_completed = []
        nodes_seen = set()
        nodes_to_explore = initial_nodes
        
        with tqdm(total=len(initial_nodes) * 4) as pbar:
            while nodes_to_explore:
                # Process nodes in batches
                batch_size = min(5, len(nodes_to_explore))
                current_batch = nodes_to_explore[:batch_size]
                nodes_to_explore = nodes_to_explore[batch_size:]
                
                # Skip already processed nodes
                current_batch = [n for n in current_batch 
                               if self._get_node_id(n) not in nodes_seen]
                if not current_batch:
                    continue
                    
                # Process the batch
                completed_attempts = self._process_node_batch(current_batch, detector)
                all_completed.extend(completed_attempts)
                
                # Update progress and analyze results
                for node in current_batch:
                    node_id = self._get_node_id(node)
                    nodes_seen.add(node_id)
                    
                    # Calculate node score and cache it
                    node_results = self._calculate_node_score(completed_attempts, detector)
                    self.node_result_cache[node_id] = node_results
                    
                    # Add child nodes if score is good enough
                    if self._should_explore_node(node_id, sum(node_results) / len(node_results)):
                        children = self._get_node_children(node)
                        siblings = self._get_node_siblings(node)
                        nodes_to_explore.extend([n for n in children + siblings 
                                              if self._get_node_id(n) not in nodes_seen])
                    
                    pbar.update(1)
                
                # Write results to file in batches
                self._write_batch_results(completed_attempts)
        
        return all_completed

    def _calculate_node_score(self, attempts, detector):
        """Calculate score for a node based on its attempts with batch processing."""
        from garak.detector_manager import get_detector_manager
        detector_manager = get_detector_manager()
        
        # Process all attempts in one batch
        batch_results = detector_manager.detect_batch(attempts, self.primary_detector)
        
        # Update attempt results and collect scores
        results = []
        for attempt, result in zip(attempts, batch_results):
            attempt.detector_results[self.primary_detector] = result
            results.extend(result if isinstance(result, list) else [result])
        """Calculate score for a node based on its attempts."""
        results = []
        for attempt in attempts:
            attempt.detector_results[self.primary_detector] = detector.detect(attempt)
            results.extend(attempt.detector_results[self.primary_detector])
        return [1.0 if s > self.per_generation_threshold else 0 for s in results]
    
    def _write_batch_results(self, attempts):
        """Write batch of results to file efficiently."""
        with open(_config.transient.reportfile.name, 'a') as f:
            for attempt in attempts:
                f.write(json.dumps(attempt.as_dict()) + '\n')
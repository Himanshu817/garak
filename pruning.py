"""Optimized pruning strategies for tree traversal."""
from typing import Dict, List, Set, Any
import numpy as np

class PruningStrategy:
    """Base class for tree pruning strategies."""
    
    def should_prune(self, node_id: str, score: float, context: Dict[str, Any]) -> bool:
        raise NotImplementedError

class StatisticalPruning(PruningStrategy):
    """Prunes branches based on statistical analysis of results."""
    
    def __init__(self, confidence_threshold: float = 0.95):
        self.confidence_threshold = confidence_threshold
        self.node_scores: Dict[str, List[float]] = {}
        
    def should_prune(self, node_id: str, score: float, context: Dict[str, Any]) -> bool:
        """Determine if a branch should be pruned based on statistical analysis."""
        if node_id not in self.node_scores:
            self.node_scores[node_id] = []
        
        self.node_scores[node_id].append(score)
        
        if len(self.node_scores[node_id]) < 5:
            return False
            
        scores = np.array(self.node_scores[node_id])
        mean = np.mean(scores)
        std = np.std(scores)
        
        if std == 0:
            return mean < context.get('threshold', 0.5)
            
        # Calculate confidence interval
        conf_interval = stats.t.interval(
            self.confidence_threshold, 
            len(scores) - 1,
            mean,
            std
        )
        
        # Prune if upper confidence bound is below threshold
        return conf_interval[1] < context.get('threshold', 0.5)

class AdaptivePruning(PruningStrategy):
    """Adapts pruning threshold based on observed success rates."""
    
    def __init__(self, initial_threshold: float = 0.5, adaption_rate: float = 0.1):
        self.threshold = initial_threshold
        self.adaption_rate = adaption_rate
        self.success_history: List[bool] = []
        
    def should_prune(self, node_id: str, score: float, context: Dict[str, Any]) -> bool:
        """Determine if a branch should be pruned with adaptive threshold."""
        # Update success history
        success = score > context.get('base_threshold', 0.5)
        self.success_history.append(success)
        
        # Adapt threshold based on recent history
        if len(self.success_history) > 10:
            recent_success_rate = sum(self.success_history[-10:]) / 10
            self.threshold = (1 - self.adaption_rate) * self.threshold + \
                           self.adaption_rate * recent_success_rate
            
        return score < self.threshold

def get_pruning_strategy(strategy_name: str = 'adaptive', **kwargs) -> PruningStrategy:
    """Factory function for pruning strategies."""
    strategies = {
        'statistical': StatisticalPruning,
        'adaptive': AdaptivePruning
    }
    
    if strategy_name not in strategies:
        raise ValueError(f"Unknown pruning strategy: {strategy_name}")
        
    return strategies[strategy_name](**kwargs)
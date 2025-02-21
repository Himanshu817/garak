"""Performance profiling utilities."""
import time
import logging
import functools
from typing import Dict, Any

class PerformanceMetrics:
    """Tracks performance metrics for different operations."""
    
    def __init__(self):
        self.metrics: Dict[str, Dict[str, Any]] = {}
    
    def record_time(self, operation: str, duration: float):
        """Record execution time for an operation."""
        if operation not in self.metrics:
            self.metrics[operation] = {
                'count': 0,
                'total_time': 0,
                'min_time': float('inf'),
                'max_time': 0
            }
        
        self.metrics[operation]['count'] += 1
        self.metrics[operation]['total_time'] += duration
        self.metrics[operation]['min_time'] = min(
            duration, self.metrics[operation]['min_time']
        )
        self.metrics[operation]['max_time'] = max(
            duration, self.metrics[operation]['max_time']
        )
    
    def get_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of performance metrics."""
        summary = {}
        for op, data in self.metrics.items():
            avg_time = data['total_time'] / data['count'] if data['count'] > 0 else 0
            summary[op] = {
                'count': data['count'],
                'total_time': round(data['total_time'], 2),
                'avg_time': round(avg_time, 2),
                'min_time': round(data['min_time'], 2),
                'max_time': round(data['max_time'], 2)
            }
        return summary

_metrics = PerformanceMetrics()

def get_metrics() -> PerformanceMetrics:
    """Get global metrics instance."""
    return _metrics

def profile_operation(operation_name: str):
    """Decorator to profile operation execution time."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                get_metrics().record_time(operation_name, duration)
        return wrapper
    return decorator
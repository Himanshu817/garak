"""Utilities for parallel processing in garak."""
import multiprocessing
from functools import partial
from typing import Any, Callable, Iterable, List, TypeVar

T = TypeVar('T')
R = TypeVar('R')

def chunk_list(lst: List[T], chunk_size: int) -> List[List[T]]:
    """Split a list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def process_in_parallel(func: Callable[[T], R],
                       items: List[T],
                       num_processes: int,
                       chunk_size: int = 1,
                       timeout: int = None) -> List[R]:
    """Process items in parallel using a pre-initialized process pool.
    
    Args:
        func: Function to apply to each item
        items: List of items to process
        num_processes: Number of processes to use
        chunk_size: Size of chunks for batch processing
        timeout: Timeout in seconds for each chunk
        
    Returns:
        List of results
    """
    if not items:
        return []
        
    chunked_items = chunk_list(items, chunk_size) if chunk_size > 1 else [[item] for item in items]
    
    def process_chunk(chunk: List[T]) -> List[R]:
        return [func(item) for item in chunk]
    
    with multiprocessing.Pool(num_processes) as pool:
        results = []
        for chunk_result in pool.imap_unordered(process_chunk, chunked_items):
            results.extend(chunk_result)
    return results
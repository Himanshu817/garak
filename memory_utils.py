"""Memory optimization utilities."""
import os
import mmap
import json
import psutil
import logging
from typing import Any, Dict, Optional
from contextlib import contextmanager

class MemoryMonitor:
    """Monitors memory usage and triggers cleanup."""
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
        self.process = psutil.Process(os.getpid())
    
    def should_cleanup(self) -> bool:
        """Check if cleanup is needed based on memory usage."""
        memory_percent = self.process.memory_percent()
        return memory_percent > self.threshold * 100

class ResultStore:
    """Memory-mapped file storage for large result sets."""
    
    def __init__(self, filename: str, buffer_size: int = 1024 * 1024):
        self.filename = filename
        self.buffer_size = buffer_size
        self._initialize_file()
    
    def _initialize_file(self):
        """Create or truncate the memory-mapped file."""
        with open(self.filename, 'wb') as f:
            f.write(b'\x00' * self.buffer_size)
    
    @contextmanager
    def get_mmap(self, mode: str = 'r+') -> mmap.mmap:
        """Get memory-mapped file handle."""
        with open(self.filename, mode='r+b') as f:
            mm = mmap.mmap(f.fileno(), 0)
            try:
                yield mm
            finally:
                mm.close()
    
    def append_result(self, result: Dict[str, Any]):
        """Append result to memory-mapped file."""
        data = json.dumps(result).encode() + b'\n'
        with self.get_mmap() as mm:
            if mm.size() - mm.tell() < len(data):
                # Grow file if needed
                new_size = mm.size() + max(self.buffer_size, len(data))
                mm.resize(new_size)
            mm.write(data)

_memory_monitor = None
_result_store = None

def get_memory_monitor() -> MemoryMonitor:
    """Get or create memory monitor instance."""
    global _memory_monitor
    if _memory_monitor is None:
        _memory_monitor = MemoryMonitor()
    return _memory_monitor

def get_result_store(filename: Optional[str] = None) -> ResultStore:
    """Get or create result store instance."""
    global _result_store
    if _result_store is None and filename is not None:
        _result_store = ResultStore(filename)
    return _result_store

def cleanup_if_needed():
    """Trigger memory cleanup if threshold is exceeded."""
    try:
        if get_memory_monitor().should_cleanup():
            logging.info("Memory threshold exceeded, triggering cleanup")
            import gc
            gc.collect()
    except Exception as e:
        logging.warning(f"Error during memory cleanup: {e}")
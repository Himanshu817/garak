"""I/O utilities for optimizing file operations."""
import json
import threading
from typing import Any, Dict, List
from queue import Queue
import logging

class BufferedFileWriter:
    """Thread-safe buffered file writer with automatic flushing."""
    
    def __init__(self, filename: str, buffer_size: int = 1000):
        self.filename = filename
        self.buffer_size = buffer_size
        self.buffer: List[str] = []
        self.lock = threading.Lock()
        self._initialize()
    
    def _initialize(self):
        """Initialize the file in write mode."""
        with open(self.filename, 'a') as f:
            f.write("")  # Ensure file exists and is writable
    
    def write(self, data: Dict[str, Any]):
        """Write data to buffer, flushing if buffer is full."""
        with self.lock:
            self.buffer.append(json.dumps(data))
            if len(self.buffer) >= self.buffer_size:
                self.flush()
    
    def flush(self):
        """Flush buffer to file."""
        if not self.buffer:
            return
            
        with self.lock:
            try:
                with open(self.filename, 'a') as f:
                    for line in self.buffer:
                        f.write(line + '\n')
                self.buffer.clear()
            except Exception as e:
                logging.error(f"Error writing to file {self.filename}: {e}")
    
    def close(self):
        """Flush remaining data and close."""
        self.flush()

# Global writer instance
_writer = None

def get_writer(filename: str = None) -> BufferedFileWriter:
    """Get or create the global buffered writer instance."""
    global _writer
    if _writer is None and filename is not None:
        _writer = BufferedFileWriter(filename)
    return _writer

def close_writer():
    """Close the global writer instance."""
    global _writer
    if _writer is not None:
        _writer.close()
        _writer = None
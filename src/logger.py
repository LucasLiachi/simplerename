import logging
import sys
from threading import Lock
from datetime import datetime
from pathlib import Path

class Logger:
    _instance = None
    _lock = Lock()
    
    LOG_LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR
    }
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize_logger()
            return cls._instance
    
    def _initialize_logger(self):
        self.logger = logging.getLogger('SimpleRename')
        self.logger.setLevel(logging.DEBUG)
        
        # Ensure logs directory exists
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(
            f'logs/simplerename_{datetime.now().strftime("%Y%m%d")}.log'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def _log(self, level: str, message: str):
        with self._lock:
            log_func = getattr(self.logger, level.lower())
            log_func(message)
    
    def debug(self, message: str):
        self._log('DEBUG', message)
    
    def info(self, message: str):
        self._log('INFO', message)
    
    def warning(self, message: str):
        self._log('WARNING', message)
    
    def error(self, message: str):
        self._log('ERROR', message)
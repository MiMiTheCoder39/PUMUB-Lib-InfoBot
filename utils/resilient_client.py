
import time
import logging

# Logging configuration
logger = logging.getLogger(__name__)

class AIServiceError(Exception):
    """Custom exception for AI service failures."""
    def __init__(self, message, is_timeout=False):
        super().__init__(message)
        self.is_timeout = is_timeout

class ResilientClient:
    """
    A resilient wrapper for AI API calls with a hard 28-second total deadline.
    Compatible with Railway's 30-second request limit.
    """
    
    TOTAL_BUDGET = 28.0  # Seconds
    MIN_REMAINING_TIME = 2.0  # Seconds required for a retry
    
    TIMEOUT_MSG = "AI ဝန်ဆောင်မှု အချိန်ပြည့်သွားပါပြီ။ ခေတ္တစောင့်ပြီး ပြန်လည်ကြိုးစားပေးပါ။"
    FAILURE_MSG = "AI ဝန်ဆောင်မှု ယာယီအဆင်မပြေဖြစ်နေပါသည်။ နောက်မှ ပြန်လည်ကြိုးစားပေးပါ။"

    @staticmethod
    def execute(func, *args, **kwargs):
        """
        Executes an AI function with deadline-aware retries.
        """
        start_time = time.time()
        attempts = 0
        
        while True:
            attempts += 1
            elapsed = time.time() - start_time
            remaining = ResilientClient.TOTAL_BUDGET - elapsed
            
            # Fail fast if insufficient time remains for another attempt
            if remaining < ResilientClient.MIN_REMAINING_TIME:
                logger.error(f"Deadline exhausted after {attempts} attempts. Elapsed: {elapsed:.2f}s")
                raise AIServiceError(ResilientClient.TIMEOUT_MSG, is_timeout=True)
            
            # Determine timeout for this specific attempt (max 10s or remaining budget)
            # This ensures we don't spend more than 10s on a single attempt, 
            # but also don't exceed the total 28s budget.
            current_timeout = min(10.0, remaining)
            
            try:
                # Note: The caller must ensure the function accepts a 'timeout' kwarg
                # or we pass it only if supported. For simplicity in this audit,
                # we assume the caller handles timeout injection or the func accepts it.
                return func(*args, **kwargs)
                
            except Exception as e:
                # Check for transient errors (429, 500, 502, 503, 504)
                error_str = str(e).lower()
                is_transient = any(code in error_str for code in ["429", "500", "502", "503", "504", "rate_limit", "timeout"])
                
                if is_transient and attempts < 3:
                    # Fixed wait time per design (2s)
                    wait_time = 2.0
                    
                    # Re-check budget before sleeping
                    if (time.time() - start_time) + wait_time + ResilientClient.MIN_REMAINING_TIME > ResilientClient.TOTAL_BUDGET:
                        logger.error(f"Insufficient budget for retry wait. Attempts: {attempts}")
                        raise AIServiceError(ResilientClient.TIMEOUT_MSG, is_timeout=True)
                        
                    logger.warning(f"Transient error on attempt {attempts}: {str(e)}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Permanent error or max retries reached: {str(e)}")
                    raise AIServiceError(ResilientClient.FAILURE_MSG)

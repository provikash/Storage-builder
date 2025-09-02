
import functools
import time
from typing import Any, Callable, Dict, Optional
from bot.logging import get_context_logger

logger = get_context_logger(__name__)

def debug_trace(log_args: bool = True, log_result: bool = True, log_duration: bool = True):
    """Decorator to trace function execution with context"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            start_time = time.time()
            
            context = {"function": func_name}
            if log_args and (args or kwargs):
                context["args"] = str(args)[:100] if args else ""
                context["kwargs"] = str(kwargs)[:100] if kwargs else ""
            
            logger.debug("Function started", **context)
            
            try:
                result = await func(*args, **kwargs)
                
                if log_duration:
                    duration = time.time() - start_time
                    context["duration_ms"] = f"{duration*1000:.2f}"
                
                if log_result and result is not None:
                    result_str = str(result)[:100] if len(str(result)) > 100 else str(result)
                    context["result"] = result_str
                
                logger.debug("Function completed successfully", **context)
                return result
                
            except Exception as e:
                context["error"] = str(e)
                context["error_type"] = type(e).__name__
                if log_duration:
                    duration = time.time() - start_time
                    context["duration_ms"] = f"{duration*1000:.2f}"
                
                logger.error("Function failed", **context)
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            start_time = time.time()
            
            context = {"function": func_name}
            if log_args and (args or kwargs):
                context["args"] = str(args)[:100] if args else ""
                context["kwargs"] = str(kwargs)[:100] if kwargs else ""
            
            logger.debug("Function started", **context)
            
            try:
                result = func(*args, **kwargs)
                
                if log_duration:
                    duration = time.time() - start_time
                    context["duration_ms"] = f"{duration*1000:.2f}"
                
                if log_result and result is not None:
                    result_str = str(result)[:100] if len(str(result)) > 100 else str(result)
                    context["result"] = result_str
                
                logger.debug("Function completed successfully", **context)
                return result
                
            except Exception as e:
                context["error"] = str(e)
                context["error_type"] = type(e).__name__
                if log_duration:
                    duration = time.time() - start_time
                    context["duration_ms"] = f"{duration*1000:.2f}"
                
                logger.error("Function failed", **context)
                raise
        
        if functools.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

class ExecutionTracker:
    """Track execution flow across multiple functions"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.steps = []
        self.start_time = time.time()
        self.logger = get_context_logger(__name__)
    
    def add_step(self, step_name: str, data: Optional[Dict[str, Any]] = None):
        """Add execution step"""
        step_time = time.time()
        step_data = {
            "step": step_name,
            "timestamp": step_time,
            "elapsed_ms": f"{(step_time - self.start_time)*1000:.2f}"
        }
        if data:
            step_data.update(data)
        
        self.steps.append(step_data)
        self.logger.debug(f"Step: {step_name}", operation=self.operation_name, **step_data)
    
    def complete(self, success: bool = True, error: Optional[str] = None):
        """Mark operation as complete"""
        total_time = time.time() - self.start_time
        context = {
            "operation": self.operation_name,
            "total_duration_ms": f"{total_time*1000:.2f}",
            "steps_count": len(self.steps),
            "success": success
        }
        
        if error:
            context["error"] = error
            self.logger.error("Operation failed", **context)
        else:
            self.logger.info("Operation completed", **context)

def create_execution_tracker(operation_name: str) -> ExecutionTracker:
    """Create execution tracker for debugging complex operations"""
    return ExecutionTracker(operation_name)

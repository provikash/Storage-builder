
from typing import Dict, Any, Type, TypeVar, Callable, Optional
from dataclasses import dataclass
import inspect
from bot.logging import LOGGER

logger = LOGGER(__name__)

T = TypeVar('T')

@dataclass
class ServiceDefinition:
    """Service definition for DI container"""
    service_type: Type
    factory: Optional[Callable] = None
    singleton: bool = True
    dependencies: list = None

class Container:
    """Simple dependency injection container"""
    
    def __init__(self):
        self._services: Dict[Type, ServiceDefinition] = {}
        self._instances: Dict[Type, Any] = {}
    
    def register(self, service_type: Type[T], factory: Callable[[], T] = None, 
                singleton: bool = True, dependencies: list = None) -> 'Container':
        """Register a service in the container"""
        self._services[service_type] = ServiceDefinition(
            service_type=service_type,
            factory=factory,
            singleton=singleton,
            dependencies=dependencies or []
        )
        return self
    
    def register_instance(self, service_type: Type[T], instance: T) -> 'Container':
        """Register a service instance"""
        self._instances[service_type] = instance
        return self
    
    def get(self, service_type: Type[T]) -> T:
        """Get a service instance"""
        # Return existing instance if singleton
        if service_type in self._instances:
            return self._instances[service_type]
        
        # Check if service is registered
        if service_type not in self._services:
            raise ValueError(f"Service {service_type.__name__} not registered")
        
        definition = self._services[service_type]
        
        # Create instance
        if definition.factory:
            # Use factory function
            instance = definition.factory()
        else:
            # Use constructor with dependency injection
            instance = self._create_instance(service_type, definition)
        
        # Store instance if singleton
        if definition.singleton:
            self._instances[service_type] = instance
        
        return instance
    
    def _create_instance(self, service_type: Type, definition: ServiceDefinition):
        """Create instance with dependency injection"""
        try:
            # Get constructor signature
            signature = inspect.signature(service_type.__init__)
            parameters = signature.parameters
            
            # Skip 'self' parameter
            param_names = [name for name in parameters.keys() if name != 'self']
            
            # Resolve dependencies
            kwargs = {}
            for param_name in param_names:
                param = parameters[param_name]
                
                # Try to resolve by type annotation
                if param.annotation != inspect.Parameter.empty:
                    try:
                        kwargs[param_name] = self.get(param.annotation)
                    except ValueError:
                        # Dependency not found, use default if available
                        if param.default != inspect.Parameter.empty:
                            kwargs[param_name] = param.default
                        else:
                            logger.warning(f"Cannot resolve dependency {param_name} for {service_type.__name__}")
            
            return service_type(**kwargs)
            
        except Exception as e:
            logger.error(f"Failed to create instance of {service_type.__name__}: {e}")
            raise

# Global container instance
container = Container()

def setup_container():
    """Setup dependency injection container with all services"""
    from bot.domains.clone.services import CloneManagementService, SubscriptionService
    from bot.infrastructure.repositories.mongo_clone_repository import MongoCloneRepository
    from bot.core.config.settings import settings
    
    # Register repositories
    container.register(MongoCloneRepository, lambda: MongoCloneRepository())
    
    # Register services
    container.register(CloneManagementService)
    container.register(SubscriptionService)
    
    # Register configuration
    container.register_instance(type(settings), settings)
    
    logger.info("Dependency injection container configured")
    return container

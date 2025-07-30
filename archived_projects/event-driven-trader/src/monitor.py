"""
API Monitor - Watches external APIs for specific conditions.
When conditions are met, creates events for the system to handle.
"""

import aiohttp
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import operator

from .events import create_api_event


logger = logging.getLogger(__name__)


class APIMonitor:
    """
    Monitors external APIs and triggers events when conditions are met.
    
    Features:
    - Async HTTP requests for efficiency
    - Configurable conditions (>, <, ==, etc)
    - Rate limiting to avoid overwhelming APIs
    - Caching to reduce API calls
    """
    
    def __init__(self, monitors_config: List[Dict[str, Any]]):
        self.monitors = monitors_config
        self.session: Optional[aiohttp.ClientSession] = None
        self.cache: Dict[str, Dict] = {}  # URL -> {data, timestamp}
        self.cache_ttl = 10  # Cache for 10 seconds
        
        # Operator mapping for condition evaluation
        self.operators = {
            '>': operator.gt,
            '<': operator.lt,
            '>=': operator.ge,
            '<=': operator.le,
            '==': operator.eq,
            '!=': operator.ne
        }
        
        # Track last check time for rate limiting
        self.last_check: Dict[str, datetime] = {}
    
    async def check_conditions(self) -> List[Any]:
        """
        Check all configured API monitors and return triggered events.
        This is called by the event loop periodically.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        triggered_events = []
        
        for monitor in self.monitors:
            if not monitor.get('enabled', True):
                continue
            
            # Rate limiting
            monitor_name = monitor['name']
            interval = monitor.get('interval', 60)
            
            if monitor_name in self.last_check:
                time_since_last = (datetime.now() - self.last_check[monitor_name]).seconds
                if time_since_last < interval:
                    continue
            
            # Check this monitor
            events = await self._check_monitor(monitor)
            triggered_events.extend(events)
            
            self.last_check[monitor_name] = datetime.now()
        
        return triggered_events
    
    async def _check_monitor(self, monitor: Dict[str, Any]) -> List[Any]:
        """Check a single API monitor for triggered conditions"""
        triggered_events = []
        
        try:
            # Fetch data from API
            data = await self._fetch_api_data(
                monitor['endpoint'],
                monitor.get('params', {})
            )
            
            if not data:
                return triggered_events
            
            # Check each condition
            for condition in monitor.get('conditions', []):
                if self._evaluate_condition(data, condition):
                    # Condition met - create event
                    event = create_api_event(
                        name=f"{monitor['name']}_{condition['handler']}",
                        handler=condition['handler'],
                        condition=self._condition_to_string(condition),
                        data={
                            'monitor': monitor['name'],
                            'api_data': data,
                            'condition': condition
                        }
                    )
                    triggered_events.append(event)
                    logger.info(f"API condition triggered: {condition}")
        
        except Exception as e:
            logger.error(f"Error checking monitor {monitor['name']}: {e}")
        
        return triggered_events
    
    async def _fetch_api_data(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """
        Fetch data from an API endpoint with caching.
        Returns None if the request fails.
        """
        # Check cache first
        cache_key = f"{endpoint}_{str(params)}"
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            age = (datetime.now() - cached['timestamp']).seconds
            if age < self.cache_ttl:
                return cached['data']
        
        # Fetch from API
        try:
            async with self.session.get(endpoint, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Update cache
                    self.cache[cache_key] = {
                        'data': data,
                        'timestamp': datetime.now()
                    }
                    
                    return data
                else:
                    logger.warning(f"API request failed: {response.status} for {endpoint}")
                    return None
        
        except Exception as e:
            logger.error(f"Error fetching from {endpoint}: {e}")
            return None
    
    def _evaluate_condition(self, data: Dict, condition: Dict) -> bool:
        """
        Evaluate if a condition is met given the API data.
        
        Example condition:
        {
            "field": "bitcoin.usd_24h_change",
            "operator": ">",
            "value": 3.0
        }
        """
        try:
            # Extract the field value from nested data
            field_value = self._get_nested_field(data, condition['field'])
            if field_value is None:
                return False
            
            # Get the operator function
            op_func = self.operators.get(condition['operator'])
            if not op_func:
                logger.warning(f"Unknown operator: {condition['operator']}")
                return False
            
            # Evaluate the condition
            return op_func(float(field_value), float(condition['value']))
        
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    def _get_nested_field(self, data: Dict, field_path: str) -> Any:
        """
        Get a value from nested dictionary using dot notation.
        Example: "bitcoin.usd_24h_change" -> data['bitcoin']['usd_24h_change']
        """
        try:
            value = data
            for key in field_path.split('.'):
                value = value[key]
            return value
        except (KeyError, TypeError):
            return None
    
    def _condition_to_string(self, condition: Dict) -> str:
        """Convert a condition dict to a readable string"""
        return f"{condition['field']} {condition['operator']} {condition['value']}"
    
    async def close(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
            self.session = None
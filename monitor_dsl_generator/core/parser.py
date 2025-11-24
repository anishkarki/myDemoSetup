"""
Monitor DSL Parser
Parses and validates YAML DSL for monitor configurations
"""

import yaml
from pathlib import Path
from typing import Dict, Any


class MonitorDSLParser:
    """Parse monitor DSL YAML configuration"""
    
    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
    
    def parse(self) -> Dict[str, Any]:
        """Parse and validate DSL configuration"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if 'monitors' not in config:
            raise ValueError("Config must contain 'monitors' key")
        
        # Validate each monitor
        for monitor in config['monitors']:
            self._validate_monitor(monitor)
        
        return config
    
    def _validate_monitor(self, monitor: Dict[str, Any]) -> None:
        """Validate a single monitor configuration"""
        required_fields = ['name', 'schedule', 'inputs', 'triggers']
        
        for field in required_fields:
            if field not in monitor:
                raise ValueError(f"Monitor '{monitor.get('name', 'unknown')}' missing required field: {field}")
        
        # Validate schedule
        schedule = monitor['schedule']
        if 'interval' not in schedule or 'unit' not in schedule:
            raise ValueError(f"Monitor '{monitor['name']}' schedule must have 'interval' and 'unit'")
        
        # Validate inputs
        inputs = monitor['inputs']
        if 'indices' not in inputs:
            raise ValueError(f"Monitor '{monitor['name']}' inputs must have 'indices'")
        
        # Validate triggers
        triggers = monitor['triggers']
        if not triggers:
            raise ValueError(f"Monitor '{monitor['name']}' must have at least one trigger")
        
        for trigger in triggers:
            if 'name' not in trigger or 'condition' not in trigger:
                raise ValueError(f"Monitor '{monitor['name']}' trigger must have 'name' and 'condition'")

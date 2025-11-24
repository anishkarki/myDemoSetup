"""
Monitor Generator
Main orchestrator for generating monitor JSON files
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from modules.query_builder import QueryBuilder
from modules.trigger_builder import TriggerBuilder
from modules.templates import MessageTemplates


class MonitorGenerator:
    """Generate OpenSearch monitor JSON files"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.query_builder = QueryBuilder()
        self.trigger_builder = TriggerBuilder()
        self.templates = MessageTemplates()
    
    def generate_all(self, output_dir: Path) -> List[Path]:
        """Generate all monitors and save to files"""
        generated_files = []
        
        for monitor_config in self.config['monitors']:
            monitor_json = self.generate_monitor(monitor_config)
            
            # Create safe filename
            safe_name = monitor_config['name'].lower()
            safe_name = safe_name.replace(' - ', '_').replace(' ', '_')
            safe_name = safe_name.replace('(', '').replace(')', '').replace(',', '')
            filename = f"{safe_name}.json"
            
            output_path = output_dir / filename
            
            with open(output_path, 'w') as f:
                json.dump(monitor_json, f, indent=2)
            
            generated_files.append(output_path)
        
        return generated_files
    
    def generate_monitor(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a single monitor JSON"""
        monitor = {
            "type": "monitor",
            "name": config['name'],
            "enabled": config.get('enabled', True),
            "schedule": {
                "period": {
                    "interval": config['schedule']['interval'],
                    "unit": config['schedule']['unit']
                }
            },
            "inputs": [
                {
                    "search": {
                        "indices": config['inputs']['indices'],
                        "query": self.query_builder.build(config['inputs'])
                    }
                }
            ],
            "triggers": [
                self.trigger_builder.build(t, self.templates) 
                for t in config.get('triggers', [])
            ]
        }
        
        return monitor

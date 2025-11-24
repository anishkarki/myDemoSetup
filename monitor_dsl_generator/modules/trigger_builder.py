"""
Trigger Builder Module
Builds OpenSearch monitor triggers
"""

from typing import Dict, Any


class TriggerBuilder:
    """Build monitor triggers"""
    
    def build(self, trigger_config: Dict[str, Any], templates) -> Dict[str, Any]:
        """Build trigger from configuration"""
        trigger = {
            "name": trigger_config['name'],
            "severity": str(trigger_config.get('severity', 1)),
            "condition": {
                "script": {
                    "source": trigger_config['condition']['script'],
                    "lang": trigger_config['condition'].get('lang', 'painless')
                }
            },
            "actions": []
        }
        
        # Build actions
        for action_config in trigger_config.get('actions', []):
            action = self._build_action(action_config, templates)
            trigger['actions'].append(action)
        
        return trigger
    
    def _build_action(self, action_config: Dict[str, Any], templates) -> Dict[str, Any]:
        """Build trigger action"""
        action = {
            "name": action_config['name'],
            "destination_id": action_config['destination_id'],
            "subject_template": {
                "source": action_config['subject_template']
            },
            "message_template": {
                "source": templates.get_template(
                    action_config.get('message_template_type', 'html_simple')
                ),
                "lang": "mustache"
            }
        }
        
        # Add throttling if specified
        throttle = action_config.get('throttle', {})
        if throttle.get('enabled', False):
            action['throttle_enabled'] = True
            action['throttle'] = {
                "value": throttle['value'],
                "unit": throttle['unit']
            }
        
        return action

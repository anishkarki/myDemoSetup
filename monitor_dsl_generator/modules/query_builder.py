"""
Query Builder Module
Builds OpenSearch queries from DSL configuration
"""

from typing import Dict, Any


class QueryBuilder:
    """Build OpenSearch queries"""
    
    def build(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Build query from inputs configuration"""
        query_type = inputs.get('query_type', 'bool_should')
        conditions = inputs.get('conditions', [])
        size = inputs.get('query_size', 100)
        time_range = inputs.get('time_range')
        sort_config = inputs.get('sort')
        aggregations = inputs.get('aggregations')
        
        # Build condition clauses
        condition_clauses = [self._build_condition(c) for c in conditions]
        
        # Add time range filter if specified
        time_filter = None
        if time_range:
            time_filter = {
                "range": {
                    "@timestamp": {
                        "gte": f"now-{time_range['value']}{time_range['unit'][0].lower()}",
                        "lte": "now"
                    }
                }
            }
        
        # Build bool query based on type
        if query_type == 'aggregation':
            bool_query = {
                "bool": {
                    "should": condition_clauses,
                    "minimum_should_match": inputs.get('minimum_should_match', 1)
                }
            }
            if time_filter:
                bool_query["bool"]["filter"] = [time_filter]
            
            query_result = {
                "query": bool_query,
                "size": 0
            }
            
            if aggregations:
                query_result["aggs"] = aggregations
            
            return query_result
        
        elif query_type == 'bool_should':
            bool_query = {
                "bool": {
                    "should": condition_clauses,
                    "minimum_should_match": inputs.get('minimum_should_match', 1)
                }
            }
            if time_filter:
                bool_query["bool"]["filter"] = [time_filter]
        
        elif query_type == 'bool_must':
            bool_query = {
                "bool": {
                    "must": condition_clauses
                }
            }
            if time_filter:
                bool_query["bool"]["filter"] = [time_filter]
        
        else:
            # Single condition
            if time_filter:
                bool_query = {
                    "bool": {
                        "must": [condition_clauses[0] if condition_clauses else {"match_all": {}}],
                        "filter": [time_filter]
                    }
                }
            else:
                bool_query = condition_clauses[0] if condition_clauses else {"match_all": {}}
        
        query_result = {
            "query": bool_query,
            "size": size
        }
        
        # Add sort if specified
        if sort_config:
            query_result["sort"] = [
                {
                    sort_config['field']: {
                        "order": sort_config.get('order', 'desc')
                    }
                }
            ]
        
        return query_result
    
    def _build_condition(self, condition: Dict[str, Any]) -> Dict[str, Any]:
        """Build a single query condition"""
        cond_type = condition.get('type')
        
        if cond_type == 'terms':
            return {
                "terms": {
                    condition['field']: condition['values']
                }
            }
        elif cond_type == 'match_phrase':
            return {
                "match_phrase": {
                    condition['field']: condition['value']
                }
            }
        elif cond_type == 'match':
            return {
                "match": {
                    condition['field']: condition['value']
                }
            }
        elif cond_type == 'range':
            return {
                "range": {
                    condition['field']: condition['range']
                }
            }
        elif cond_type == 'wildcard':
            return {
                "wildcard": {
                    condition['field']: condition['value']
                }
            }
        else:
            raise ValueError(f"Unknown condition type: {cond_type}")

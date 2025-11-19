#!/usr/bin/env python3
"""
Test Suite for OpenSearch Monitor Generator
Tests monitor generation, query building, and template rendering
"""

import unittest
import json
import yaml
import tempfile
import shutil
from pathlib import Path
from generate_monitors import MonitorGenerator


class TestMonitorGenerator(unittest.TestCase):
    """Test cases for MonitorGenerator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.config_path = self.test_dir / "test_config.yml"
        
        # Sample test configuration
        self.test_config = {
            'monitors': [
                {
                    'name': 'Test Monitor - Critical Errors',
                    'enabled': True,
                    'schedule': {
                        'interval': 1,
                        'unit': 'MINUTES'
                    },
                    'inputs': {
                        'indices': ['test_index*', 'logs'],
                        'query_type': 'bool_should',
                        'query_size': 50,
                        'conditions': [
                            {
                                'type': 'terms',
                                'field': 'error_code',
                                'values': ['500', '503', '504']
                            },
                            {
                                'type': 'match_phrase',
                                'field': 'message',
                                'value': 'CRITICAL'
                            }
                        ],
                        'minimum_should_match': 1
                    },
                    'triggers': [
                        {
                            'name': 'Error Alert',
                            'severity': 1,
                            'condition': {
                                'script': 'return ctx.results[0].hits.total.value > 0;',
                                'lang': 'painless'
                            },
                            'actions': [
                                {
                                    'name': 'Email Alert',
                                    'type': 'email',
                                    'destination_id': 'test-dest-id',
                                    'subject_template': 'Alert: {{ctx.monitor.name}}',
                                    'message_template_type': 'html_simple',
                                    'throttle': {
                                        'enabled': True,
                                        'value': 10,
                                        'unit': 'MINUTES'
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        
        # Write test config to file
        with open(self.config_path, 'w') as f:
            yaml.dump(self.test_config, f)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.test_dir)
    
    def test_load_config(self):
        """Test YAML config loading"""
        generator = MonitorGenerator(str(self.config_path))
        self.assertIn('monitors', generator.config)
        self.assertEqual(len(generator.config['monitors']), 1)
        self.assertEqual(
            generator.config['monitors'][0]['name'],
            'Test Monitor - Critical Errors'
        )
    
    def test_build_terms_condition(self):
        """Test terms query condition building"""
        generator = MonitorGenerator(str(self.config_path))
        condition = {
            'type': 'terms',
            'field': 'status_code',
            'values': ['500', '502', '503']
        }
        result = generator._build_query_condition(condition)
        
        self.assertIn('terms', result)
        self.assertIn('status_code', result['terms'])
        self.assertEqual(result['terms']['status_code'], ['500', '502', '503'])
    
    def test_build_match_phrase_condition(self):
        """Test match_phrase query condition building"""
        generator = MonitorGenerator(str(self.config_path))
        condition = {
            'type': 'match_phrase',
            'field': 'message',
            'value': 'ERROR'
        }
        result = generator._build_query_condition(condition)
        
        self.assertIn('match_phrase', result)
        self.assertIn('message', result['match_phrase'])
        self.assertEqual(result['match_phrase']['message'], 'ERROR')
    
    def test_build_bool_should_query(self):
        """Test bool should query building"""
        generator = MonitorGenerator(str(self.config_path))
        inputs = {
            'query_type': 'bool_should',
            'query_size': 100,
            'conditions': [
                {
                    'type': 'terms',
                    'field': 'error_code',
                    'values': ['500', '503']
                },
                {
                    'type': 'match_phrase',
                    'field': 'message',
                    'value': 'FATAL'
                }
            ],
            'minimum_should_match': 1
        }
        
        result = generator._build_query(inputs)
        
        self.assertIn('query', result)
        self.assertIn('bool', result['query'])
        self.assertIn('should', result['query']['bool'])
        self.assertEqual(len(result['query']['bool']['should']), 2)
        self.assertEqual(result['query']['bool']['minimum_should_match'], 1)
        self.assertEqual(result['size'], 100)
    
    def test_build_bool_must_query(self):
        """Test bool must query building"""
        generator = MonitorGenerator(str(self.config_path))
        inputs = {
            'query_type': 'bool_must',
            'conditions': [
                {
                    'type': 'match',
                    'field': 'status',
                    'value': 'error'
                }
            ]
        }
        
        result = generator._build_query(inputs)
        
        self.assertIn('bool', result['query'])
        self.assertIn('must', result['query']['bool'])
    
    def test_get_message_templates(self):
        """Test message template retrieval"""
        generator = MonitorGenerator(str(self.config_path))
        
        # Test HTML grouped template
        template = generator._get_message_template('html_grouped_by_host')
        self.assertIn('{{#grouped_hosts}}', template)
        self.assertIn('<table>', template)
        
        # Test HTML simple template
        template = generator._get_message_template('html_simple')
        self.assertIn('{{#ctx.results.0.hits.hits}}', template)
        self.assertIn('<table>', template)
        
        # Test plain text template
        template = generator._get_message_template('plain_text')
        self.assertIn('Monitor:', template)
        self.assertNotIn('<html>', template)
    
    def test_build_action(self):
        """Test action building"""
        generator = MonitorGenerator(str(self.config_path))
        action_config = {
            'name': 'Test Email',
            'destination_id': 'dest-123',
            'subject_template': 'Alert: Test',
            'message_template_type': 'html_simple',
            'throttle': {
                'enabled': True,
                'value': 15,
                'unit': 'MINUTES'
            }
        }
        
        result = generator._build_action(action_config)
        
        self.assertEqual(result['name'], 'Test Email')
        self.assertEqual(result['destination_id'], 'dest-123')
        self.assertIn('subject_template', result)
        self.assertIn('message_template', result)
        self.assertTrue(result['throttle_enabled'])
        self.assertEqual(result['throttle']['value'], 15)
    
    def test_build_trigger(self):
        """Test trigger building"""
        generator = MonitorGenerator(str(self.config_path))
        trigger_config = {
            'name': 'Test Trigger',
            'severity': 2,
            'condition': {
                'script': 'return true;',
                'lang': 'painless'
            },
            'actions': [
                {
                    'name': 'Email',
                    'destination_id': 'dest-id',
                    'subject_template': 'Alert',
                    'message_template_type': 'html_simple',
                    'throttle': {
                        'enabled': False
                    }
                }
            ]
        }
        
        result = generator._build_trigger(trigger_config)
        
        self.assertEqual(result['name'], 'Test Trigger')
        self.assertEqual(result['severity'], '2')
        self.assertIn('condition', result)
        self.assertEqual(result['condition']['script']['source'], 'return true;')
        self.assertEqual(len(result['actions']), 1)
    
    def test_generate_monitor(self):
        """Test complete monitor generation"""
        generator = MonitorGenerator(str(self.config_path))
        monitor_config = self.test_config['monitors'][0]
        
        result = generator.generate_monitor(monitor_config)
        
        # Validate monitor structure
        self.assertEqual(result['type'], 'monitor')
        self.assertEqual(result['name'], 'Test Monitor - Critical Errors')
        self.assertTrue(result['enabled'])
        
        # Validate schedule
        self.assertEqual(result['schedule']['period']['interval'], 1)
        self.assertEqual(result['schedule']['period']['unit'], 'MINUTES')
        
        # Validate inputs
        self.assertEqual(len(result['inputs']), 1)
        self.assertIn('search', result['inputs'][0])
        self.assertEqual(
            result['inputs'][0]['search']['indices'],
            ['test_index*', 'logs']
        )
        
        # Validate query
        query = result['inputs'][0]['search']['query']
        self.assertIn('query', query)
        self.assertIn('bool', query['query'])
        self.assertIn('should', query['query']['bool'])
        
        # Validate triggers
        self.assertEqual(len(result['triggers']), 1)
        self.assertEqual(result['triggers'][0]['name'], 'Error Alert')
        
        # Validate actions
        actions = result['triggers'][0]['actions']
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['name'], 'Email Alert')
    
    def test_generate_all(self):
        """Test generating all monitors to files"""
        generator = MonitorGenerator(str(self.config_path))
        output_dir = self.test_dir / 'output'
        
        generated_files = generator.generate_all(str(output_dir))
        
        self.assertEqual(len(generated_files), 1)
        self.assertTrue(generated_files[0].exists())
        
        # Validate generated JSON
        with open(generated_files[0], 'r') as f:
            monitor = json.load(f)
        
        self.assertEqual(monitor['type'], 'monitor')
        self.assertEqual(monitor['name'], 'Test Monitor - Critical Errors')
    
    def test_invalid_condition_type(self):
        """Test handling of invalid condition type"""
        generator = MonitorGenerator(str(self.config_path))
        condition = {
            'type': 'invalid_type',
            'field': 'test'
        }
        
        with self.assertRaises(ValueError):
            generator._build_query_condition(condition)
    
    def test_missing_config_file(self):
        """Test handling of missing config file"""
        with self.assertRaises(FileNotFoundError):
            MonitorGenerator('/nonexistent/path/config.yml')
    
    def test_range_condition(self):
        """Test range query condition building"""
        generator = MonitorGenerator(str(self.config_path))
        condition = {
            'type': 'range',
            'field': 'response_time',
            'range': {
                'gte': 1000,
                'lte': 5000
            }
        }
        result = generator._build_query_condition(condition)
        
        self.assertIn('range', result)
        self.assertIn('response_time', result['range'])
        self.assertEqual(result['range']['response_time']['gte'], 1000)
        self.assertEqual(result['range']['response_time']['lte'], 5000)
    
    def test_action_without_throttle(self):
        """Test action building without throttle"""
        generator = MonitorGenerator(str(self.config_path))
        action_config = {
            'name': 'No Throttle Email',
            'destination_id': 'dest-456',
            'subject_template': 'Alert',
            'message_template_type': 'plain_text',
            'throttle': {
                'enabled': False
            }
        }
        
        result = generator._build_action(action_config)
        
        self.assertNotIn('throttle_enabled', result)
        self.assertNotIn('throttle', result)
    
    def test_multiple_monitors(self):
        """Test generating multiple monitors"""
        # Add second monitor to config
        second_monitor = {
            'name': 'Second Test Monitor',
            'enabled': False,
            'schedule': {
                'interval': 5,
                'unit': 'MINUTES'
            },
            'inputs': {
                'indices': ['logs2'],
                'query_type': 'bool_should',
                'conditions': [
                    {
                        'type': 'match',
                        'field': 'level',
                        'value': 'warning'
                    }
                ]
            },
            'triggers': [
                {
                    'name': 'Warning Trigger',
                    'severity': 3,
                    'condition': {
                        'script': 'return ctx.results[0].hits.total.value > 10;'
                    },
                    'actions': []
                }
            ]
        }
        
        self.test_config['monitors'].append(second_monitor)
        
        with open(self.config_path, 'w') as f:
            yaml.dump(self.test_config, f)
        
        generator = MonitorGenerator(str(self.config_path))
        output_dir = self.test_dir / 'multi_output'
        
        generated_files = generator.generate_all(str(output_dir))
        
        self.assertEqual(len(generated_files), 2)
        
        # Verify both files exist and contain valid JSON
        for file_path in generated_files:
            self.assertTrue(file_path.exists())
            with open(file_path, 'r') as f:
                monitor = json.load(f)
                self.assertEqual(monitor['type'], 'monitor')


class TestIntegration(unittest.TestCase):
    """Integration tests using real config file"""
    
    def test_real_config_generation(self):
        """Test generation with actual opensearch_dsl.yml"""
        config_path = Path(__file__).parent / 'opensearch_dsl.yml'
        
        if not config_path.exists():
            self.skipTest('opensearch_dsl.yml not found')
        
        generator = MonitorGenerator(str(config_path))
        
        # Generate to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            generated_files = generator.generate_all(temp_dir)
            
            self.assertGreater(len(generated_files), 0)
            
            for file_path in generated_files:
                self.assertTrue(file_path.exists())
                
                # Validate JSON structure
                with open(file_path, 'r') as f:
                    monitor = json.load(f)
                
                # Check required fields
                self.assertEqual(monitor['type'], 'monitor')
                self.assertIn('name', monitor)
                self.assertIn('schedule', monitor)
                self.assertIn('inputs', monitor)
                self.assertIn('triggers', monitor)
                
                # Validate schedule structure
                self.assertIn('period', monitor['schedule'])
                self.assertIn('interval', monitor['schedule']['period'])
                self.assertIn('unit', monitor['schedule']['period'])
                
                # Validate inputs structure
                self.assertGreater(len(monitor['inputs']), 0)
                self.assertIn('search', monitor['inputs'][0])
                self.assertIn('indices', monitor['inputs'][0]['search'])
                self.assertIn('query', monitor['inputs'][0]['search'])
                
                # Validate triggers structure
                self.assertGreater(len(monitor['triggers']), 0)
                trigger = monitor['triggers'][0]
                self.assertIn('name', trigger)
                self.assertIn('severity', trigger)
                self.assertIn('condition', trigger)
                self.assertIn('actions', trigger)


def run_tests():
    """Run all tests and display results"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestMonitorGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✓ ALL TESTS PASSED")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    exit_code = run_tests()
    exit(exit_code)

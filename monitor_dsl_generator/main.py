#!/usr/bin/env python3
"""
OpenSearch Monitor DSL Generator
Generates OpenSearch monitor JSON files from YAML DSL
"""

import sys
import argparse
from pathlib import Path
from core.parser import MonitorDSLParser
from core.generator import MonitorGenerator


def main():
    parser = argparse.ArgumentParser(
        description='Generate OpenSearch monitors from YAML DSL'
    )
    parser.add_argument(
        'config',
        type=str,
        help='Path to monitor DSL YAML file'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='monitors',
        help='Output directory for generated monitors (default: monitors)'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate configuration without generating files'
    )
    
    args = parser.parse_args()
    
    # Parse and validate
    print(f"📖 Parsing DSL configuration: {args.config}")
    try:
        dsl_parser = MonitorDSLParser(args.config)
        config = dsl_parser.parse()
        
        print(f"✓ Configuration valid ({len(config['monitors'])} monitor(s) defined)")
        
        if args.validate_only:
            return 0
        
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1
    
    # Generate monitors
    print(f"\n🔧 Generating monitor JSON files...")
    try:
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generator = MonitorGenerator(config)
        generated_files = generator.generate_all(output_dir)
        
        print(f"\n✓ Successfully generated {len(generated_files)} monitor(s):")
        for file in generated_files:
            print(f"  ✓ {file}")
        
        print(f"\n📁 Monitors saved to: {output_dir.absolute()}")
        print(f"\n🚀 To post monitors to OpenSearch:")
        for file in generated_files:
            print(f"  curl -X POST 'http://localhost:9200/_plugins/_alerting/monitors' \\")
            print(f"    -H 'Content-Type: application/json' \\")
            print(f"    -d @{file}\n")
        
        return 0
        
    except Exception as e:
        print(f"✗ Generation error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

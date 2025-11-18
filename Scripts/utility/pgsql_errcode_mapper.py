#!/usr/bin/env python3
"""
Fetch PostgreSQL errcodes appendix and generate a JSON mapping of SQLSTATE codes
to heuristic severity categories (highest / medium / normal).

Usage:
  python Scripts/utility/pgsql_errcode_mapper.py

Outputs:
  Scripts/utility/pgsql_errcode_severity.json

The mapping is heuristic: it classifies codes by SQLSTATE class prefixes.
You can edit the `CLASS_SEVERITY` mapping in this script to tune results.
"""
from __future__ import annotations
import json
import re
import sys
from urllib.request import urlopen

URL = 'https://www.postgresql.org/docs/current/errcodes-appendix.html'
OUT_PATH = 'Scripts/utility/pgsql_errcode_severity.json'

# Heuristic mapping from SQLSTATE class (first 2 chars) to severity bucket.
# Tweak these sets to reflect your operational preferences.
HIGHEST_CLASSES = set(['XX', 'F0', '58', '57', '53', '54', '55'])
MEDIUM_CLASSES = set(['40', '23', '22', '42', '28', '25', '3B', '3D', '39', '2F', '2D', '2B', '21'])

def severity_for_code(code: str) -> str:
    """Return one of 'highest', 'medium', or 'normal' for a given SQLSTATE code."""
    if not code or len(code) < 2:
        return 'normal'
    prefix = code[:2]
    # Normalize to upper-case for comparison
    prefix = prefix.upper()
    if prefix in HIGHEST_CLASSES:
        return 'highest'
    if prefix in MEDIUM_CLASSES:
        return 'medium'
    # Treat success/warning/no-data as normal/low priority
    if prefix in ('00', '01', '02'):
        return 'normal'
    # Default fallback
    return 'normal'

def preferred_level_for_severity(sev: str) -> str:
    """Map our bucket to a likely Postgres severity label for alert actions."""
    if sev == 'highest':
        return 'FATAL'
    if sev == 'medium':
        return 'ERROR'
    return 'WARNING'

def extract_codes_from_html(html: str) -> dict:
    """Return dict mapping SQLSTATE code -> short name/description.

    The page is an HTML table; we strip tags and search for five-character codes
    followed by a condition name. This is intentionally permissive so it works
    even if the page formatting changes slightly.
    """
    # Strip HTML tags (simple approach)
    text = re.sub(r'<[^>]+>', ' ', html)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    # Find tokens that look like SQLSTATE codes (5 chars of letters/digits)
    # followed by a short condition name (letters, digits, underscore).
    pattern = re.compile(r'\b([0-9A-Z]{5})\b\s+([a-z0-9_]+)', re.I)
    found = pattern.findall(text)

    codes = {}
    for code, name in found:
        code = code.upper()
        # guard against false matches like table/section numbers
        if not re.match(r'^[0-9A-Z]{5}$', code):
            continue
        # prefer the first observed name for a code
        if code not in codes:
            codes[code] = name
    return codes

def main() -> int:
    print('Fetching', URL)
    try:
        with urlopen(URL, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except Exception as exc:
        print('Error fetching page:', exc, file=sys.stderr)
        return 2

    codes = extract_codes_from_html(html)
    print(f'Found {len(codes)} candidate codes')

    mapping = {}
    for code, name in sorted(codes.items()):
        cls = code[:2].upper()
        sev = severity_for_code(code)
        mapping[code] = {
            'condition_name': name,
            'class': cls,
            'severity': sev,
            'preferred_level': preferred_level_for_severity(sev),
        }

    # Write JSON file
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, sort_keys=True)

    # Print a small summary
    totals = {'highest':0, 'medium':0, 'normal':0}
    for v in mapping.values():
        totals[v['severity']] += 1
    print('Summary:', totals)
    print('Wrote:', OUT_PATH)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

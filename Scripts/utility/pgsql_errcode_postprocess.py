#!/usr/bin/env python3
"""
Post-process the `pgsql_errcode_severity.json` produced by the mapper and
produce:

- `pgsql_errcode_severity_buckets.json` : codes grouped by severity
- `pgsql_errcode_regexes.json` : safe regex strings for each severity (joined with |)
- `config_snippet_monitors.ini` : a ready-to-drop `config.ini` snippet with three monitor sections

Run this in the repo root. It expects `Scripts/utility/pgsql_errcode_severity.json` to exist.
"""
from __future__ import annotations
import json
import os
import re

IN_PATH = 'Scripts/utility/pgsql_errcode_severity.json'
OUT_BUCKETS = 'Scripts/utility/pgsql_errcode_severity_buckets.json'
OUT_REGEX = 'Scripts/utility/pgsql_errcode_regexes.json'
OUT_SNIPPET = 'Scripts/utility/config_snippet_monitors.ini'

def load_mapping(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as fh:
        return json.load(fh)

def make_safe_regex_for_codes(codes: list) -> str:
    # Escape codes for regex; SQLSTATE codes are alnum so escaping is trivial,
    # but do it robustly in case.
    esc = [re.escape(c) for c in sorted(set(codes))]
    # Join with | and wrap in non-capturing group and word boundaries
    return r"\b(?:" + "|".join(esc) + r")\b"

def main():
    if not os.path.exists(IN_PATH):
        print('Input mapping not found:', IN_PATH)
        return 2
    mapping = load_mapping(IN_PATH)

    buckets = {'highest': [], 'medium': [], 'normal': []}
    for code, info in mapping.items():
        sev = info.get('severity', 'normal')
        if sev not in buckets:
            buckets['normal'].append(code)
        else:
            buckets[sev].append(code)

    # write buckets file
    with open(OUT_BUCKETS, 'w', encoding='utf-8') as fh:
        json.dump(buckets, fh, indent=2, sort_keys=True)

    # make regexes
    regexes = {sev: make_safe_regex_for_codes(codes) for sev, codes in buckets.items()}
    with open(OUT_REGEX, 'w', encoding='utf-8') as fh:
        json.dump(regexes, fh, indent=2, sort_keys=True)

    # create config snippet with three monitors using structured field `error.code`
    snippet = []
    snippet.append('[monitor:fatal_panic_highest]')
    snippet.append('indices = postgres-*')
    snippet.append('use_structured_code = true')
    snippet.append('match_field = error.code')
    snippet.append('match_type = regex')
    snippet.append(f"match_value = {regexes['highest']}")
    snippet.append('window = 5m')
    snippet.append('threshold = 1')
    snippet.append('per_host_threshold = 1')
    snippet.append('by_host = true')
    snippet.append('sample_size_per_host = 3')
    snippet.append('severity = 1')
    snippet.append('')

    snippet.append('[monitor:error_medium]')
    snippet.append('indices = postgres-*')
    snippet.append('use_structured_code = true')
    snippet.append('match_field = error.code')
    snippet.append('match_type = regex')
    snippet.append(f"match_value = {regexes['medium']}")
    snippet.append('window = 10m')
    snippet.append('threshold = 5')
    snippet.append('per_host_threshold = 5')
    snippet.append('by_host = true')
    snippet.append('sample_size_per_host = 5')
    snippet.append('severity = 2')
    snippet.append('')

    snippet.append('[monitor:error_normal]')
    snippet.append('indices = postgres-*')
    snippet.append('use_structured_code = true')
    snippet.append('match_field = error.code')
    snippet.append('match_type = regex')
    snippet.append(f"match_value = {regexes['normal']}")
    snippet.append('window = 30m')
    snippet.append('threshold = 10')
    snippet.append('per_host_threshold = 10')
    snippet.append('by_host = true')
    snippet.append('sample_size_per_host = 3')
    snippet.append('severity = 3')

    with open(OUT_SNIPPET, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(snippet))

    print('Wrote:', OUT_BUCKETS)
    print('Wrote:', OUT_REGEX)
    print('Wrote:', OUT_SNIPPET)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

# DSL Generator (OpenSearch monitors) — README

This folder contains the enhanced DSL generator `dsl_generator.py` which produces OpenSearch Alerting monitor JSON files from a `config.ini` file, and a unit test harness `../test_dsl_generator.py` which validates generation.

Prerequisites
- Python 3.8+ (no external packages required).
- Optional: `curl` and `jq` for pushing monitors and inspecting the cluster.

Quick start

1. From the repository root, generate monitors with the bundled config:

```bash
python3 Scripts/utility/dsl_generator.py --config Scripts/config.ini
```

- The script writes JSON files into the `output_dir` configured in `Scripts/config.ini` (default: `monitors`).
- Example generated filenames: `monitors/monitor_error_5min.json`, `monitors/monitor_fatal_panic.json`.

Running tests

From the repository root run the test module (the test knows how to find `Scripts/config.ini`):

```bash
python3 Scripts/test_dsl_generator.py
# or using unittest discovery
python3 -m unittest Scripts/test_dsl_generator.py
```

What the test does
- Executes the generator (`Scripts/utility/dsl_generator.py --config Scripts/config.ini`).
- Reads `output_dir` from the config and asserts that at least one monitor JSON was created.
- Performs basic JSON schema checks (presence of `name`, `inputs`, `triggers`).

Config overview (`Scripts/config.ini`)
- Sections named `monitor:<monitor_name>` define monitors. Example:

```
[monitor:fatal_panic]
indices = postgres*
interval = 1
interval_unit = MINUTES
window = 1m
match_value = FATAL|PANIC
host_pattern = 87b4cc23*
sample_size = 3
threshold = 1
destination_id = your_webhook_config_id
```

- The `[general]` section controls global options such as `output_dir` and optional `mapping_file`.

Pushing monitors to OpenSearch

- Create a notification channel (webhook/email) in OpenSearch Notifications first and obtain its `destination_id`.
- To create a monitor from a generated JSON file (create):

```bash
curl -k -u admin:OpenSearch@2024 \
  -H 'Content-Type: application/json' \
  -X POST https://localhost:19200/_plugins/_alerting/monitors \
  -d @monitors/monitor_error_5min.json
```

- To update an existing monitor (replace actions), use the monitor id returned when creating and `PUT`:

```bash
curl -k -u admin:OpenSearch@2024 \
  -H 'Content-Type: application/json' \
  -X PUT https://localhost:19200/_plugins/_alerting/monitors/<MONITOR_ID> \
  -d @monitors/monitor_error_5min.json
```

Notes and tips
- The generator will use a mapping file if `mapping_file` is set in `[general]`. You can dump index mappings to a file and point to it for better field resolution.
- The generator embeds Mustache templates in `message_template.source`. If you intend to send raw JSON to your webhook, ensure the webhook channel accepts Mustache templating and raw JSON bodies.
- If you want the generator to automatically POST monitors for you, I can add a `--push` flag that uses environment variables for credentials and endpoint (ask me to add it).

Troubleshooting
- If you see `No monitor JSON files generated`, open `Scripts/config.ini` and ensure it contains at least one `[monitor:<name>]` section.
- If pushing monitors fails with HTTP 401/403, verify your OpenSearch credentials and that the Notifications plugin is enabled.

Contact
- If you want, I can update the generator to emit the exact webhook JSON body template you prefer or add an automatic push flow. Tell me which you prefer.

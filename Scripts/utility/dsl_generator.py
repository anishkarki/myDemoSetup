from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ChannelConfig:
    name: str
    description: str
    channel_type: str
    sender: str
    default_recipients: List[str]
    last_updated: str
    destination_id: Optional[str] = None  # OpenSearch destination identifier (if available)


def _base_action_message(channel: ChannelConfig, index: str) -> str:
    recipients = ", ".join(channel.default_recipients)
    return (
        f"Name: Panic & FATAL Error Monitor\n"
        f"Description: Filters panic/fatal text from error logs and emails the team.\n"
        f"Channel name: {channel.name}\n"
        f"Channel type: {channel.channel_type}\n"
        f"Sender: {channel.sender}\n"
        f"Recipients: {recipients}\n"
        f"Last updated: {channel.last_updated}\n"
        f"Index: {index}\n"
        "Alert fires when any log line contains panic or fatal text.\n"
        "Recent findings:\n"
        "{{#ctx.results.0.hits.hits}}\n"
        "- {{_source.@timestamp}} :: {{_source.message}}"
        "{{/ctx.results.0.hits.hits}}\n"
    )


def build_panic_fatal_email_monitor(
    channel: ChannelConfig,
    index: str,
    schedule_interval_minutes: int = 5,
) -> Dict:
    """
    Create an OpenSearch Alerting monitor DSL for panic/fatal detection routed to the given channel.
    """
    query = {
        "size": 5,
        "query": {
            "bool": {
                "should": [
                    {"match_phrase": {"message": "panic"}},
                    {"match_phrase": {"message": "PANIC"}},
                    {"match_phrase": {"message": "fatal"}},
                    {"match_phrase": {"message": "FATAL"}},
                ],
                "minimum_should_match": 1,
            }
        },
        "sort": [{"@timestamp": {"order": "desc"}}],
        "_source": ["@timestamp", "message", "level", "_raw"],
    }

    action = {
        "name": f"Email {channel.name}",
        "destination_id": channel.destination_id or channel.name,
        "throttle_enabled": False,
        "subject_template": {"source": "[Alert] Panic/FATAL errors detected"},
        "message_template": {"source": _base_action_message(channel, index)},
    }

    monitor = {
        "name": "panic_fatal_email_monitor",
        "type": "monitor",
        "enabled": True,
        "enabled_time": 0,
        "schedule": {"period": {"interval": schedule_interval_minutes, "unit": "MINUTES"}},
        "inputs": [{"search": {"indices": [index], "query": query}}],
        "triggers": [
            {
                "name": "panic_fatal_trigger",
                "severity": "1",
                "condition": {
                    "script": {"source": "return ctx.results[0].hits.total.value > 0", "lang": "painless"}
                },
                "actions": [action],
            }
        ],
    }

    return monitor

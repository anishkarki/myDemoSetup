from pathlib import Path
import json

from opensearchpy import OpenSearch

from utility import (
    ChannelConfig,
    build_panic_fatal_email_monitor,
    get_logger,
    load_kv_secret,
)

host = "localhost"
port = 19200

log = get_logger(__name__)


def load_auth(secret_path: Path):
    """Load OpenSearch credentials from a simple key/value secret file."""
    creds = load_kv_secret(secret_path, required_keys=("OS_USERNAME", "OS_PASSWORD"))
    return creds["OS_USERNAME"], creds["OS_PASSWORD"]


auth = load_auth(Path(__file__).resolve().parent / ".secret")

client = OpenSearch(
    hosts=[{"host": host, "port": port}],
    http_compres=True,
    http_auth=auth,
    use_ssl=True,
    verify_certs=False,
    ssl_asserts_hostname=False,
    ssl_show_warn=False,
)

# View all the details about the indices
def get_index_metainfo(client=None, index=None, format='json'):
    return client.cat.indices(index=index, format=format)

# view index mapping and settings
def get_index_mapandSettings(client=None, index=None):
    respose =  client.indices.get(index=index)
    return json.dumps(respose)

def get_logs_orderbydate(client=None, index=None, size=0):
    query = {
        "size": size,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "query": {"match_all": {}},
        "_source": ["@timestamp", "_raw", "level"]
    }
    resp = client.search(index=index, body=query)
    for hit in resp['hits']['hits']:
        raw_log = hit['_source'].get('_raw', hit['_source'].get('message', 'N/A'))
        ts = hit['_source']['@timestamp']
        print(f"[{ts}] Full log:\n {raw_log}\n {'-'*80}")


info = get_index_metainfo(client, index='postgreslogs', format='json')
print(info[0])

respose = get_index_mapandSettings(client, index='postgreslogs')
print(respose)

get_logs_orderbydate(client, index='postgreslogs', size=100)


channel = ChannelConfig(
    name="Test Email Channel",
    description="Sends via Mailhog",
    channel_type="Email",
    sender="Mailhog SMTP",
    default_recipients=["Dev Team"],
    last_updated="11/06/25 7:11 pm AEDT",
    destination_id="Test Email Channel",  # update with your OpenSearch destination id if needed
)

monitor_dsl = build_panic_fatal_email_monitor(
    channel=channel,
    index="postgreslogs",
    schedule_interval_minutes=5,
)

log.info("Generated Panic/FATAL monitor DSL:\n%s", json.dumps(monitor_dsl, indent=2))

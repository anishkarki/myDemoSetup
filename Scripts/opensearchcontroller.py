from opensearchpy import OpenSearch 

host = 'localhost'
port = 19200
auth = ('admin','OpenSearch@2024')

client = OpenSearch(
    hosts=[{'host':host, 'port': port}],
    http_compres=True,
    http_auth=auth,
    use_ssl=True,
    verify_certs=False,
    ssl_asserts_hostname=False,
    ssl_show_warn=False
)
print(client.info())

metadata = client.cluster.state(metric='metadata')

for index_name in metadata['metadata']['indices']:
    print(index_name)

for idx in client.indices.get_alias("*"):
    stats = client.indices.stats(index=idx)
    print(f"{idx}: docs={stats['_all']['primaries']['docs']['count']}")
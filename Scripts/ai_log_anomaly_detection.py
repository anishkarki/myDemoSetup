import pandas as pd
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt

# Load your log data (replace with your actual log file or DataFrame source)
# Example: logs = pd.read_csv('postgres_logs.csv')
logs = pd.read_json('postgres_logs.json', lines=True)

# Feature engineering: extract relevant features for anomaly detection
# Example: count connection failures per minute, resource usage stats
logs['timestamp'] = pd.to_datetime(logs['@timestamp'])
logs['minute'] = logs['timestamp'].dt.floor('min')

# Example: connection failure pattern
def is_conn_fail(row):
    msg = str(row['_raw']).lower()
    return (
        'connection' in msg and (
            'fail' in msg or 'timeout' in msg or 'refused' in msg or 'broken pipe' in msg
        )
    )
logs['conn_fail'] = logs.apply(is_conn_fail, axis=1)

# Example: resource usage pattern (customize as needed)
def extract_cpu(row):
    msg = str(row['_raw'])
    # Dummy: look for 'cpu=xx' in log, else 0
    import re
    m = re.search(r'cpu=(\d+)', msg)
    return int(m.group(1)) if m else 0
logs['cpu'] = logs.apply(extract_cpu, axis=1)

# Aggregate per minute
groups = logs.groupby('minute').agg({
    'conn_fail': 'sum',
    'cpu': 'mean',
    '_raw': 'count'
}).rename(columns={'_raw': 'log_count'})

# Prepare features for anomaly detection
features = groups[['conn_fail', 'cpu', 'log_count']]

# Fit Isolation Forest for anomaly detection
model = IsolationForest(contamination=0.05, random_state=42)
groups['anomaly'] = model.fit_predict(features)

# Visualize spikes
plt.figure(figsize=(12,6))
plt.plot(groups.index, groups['conn_fail'], label='Connection Failures')
plt.plot(groups.index, groups['cpu'], label='Avg CPU')
plt.scatter(groups.index[groups['anomaly'] == -1], groups['conn_fail'][groups['anomaly'] == -1], color='red', label='Anomaly')
plt.legend()
plt.title('Log Anomaly Detection: Connection Failures & Resource Usage')
plt.xlabel('Time')
plt.ylabel('Count / CPU')
plt.tight_layout()
plt.show()

# Print anomaly windows
detected = groups[groups['anomaly'] == -1]
print('Anomaly windows:')
print(detected[['conn_fail', 'cpu', 'log_count']])

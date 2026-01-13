import json, statistics
with open('artifacts/db_query_count_per_request.json') as f:
    d = json.load(f)
for k in ('baseline','optimized'):
    arr = d[k]
    print(k, 'count=', len(arr), 'mean={:.2f}'.format(statistics.mean(arr)), 'median={}'.format(statistics.median(arr)), 'min=', min(arr), 'max=', max(arr))

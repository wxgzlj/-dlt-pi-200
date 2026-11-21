# Data directory

Generated source snapshots belong here locally and should not be committed unless explicitly reviewed.

Run:
`python src/fetch_history.py --output-dir data/history_snapshot`

The downloader uses the official Sports Lottery API endpoint:
`https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry`
with `gameNo=85`.

It stores raw page responses, a normalized CSV, and a manifest containing retrieval time and SHA-256 hashes. The snapshot retrieval timestamp is assigned to all rows as a conservative `published_at_utc` proxy. Therefore the snapshot is eligible only for forecast cutoffs strictly later than its retrieval timestamp. Do not backdate it.

The downloader does not prove the historical dataset is complete merely because pagination ended. Verify the first/last issue range, issue continuity, official result announcements, and any corrections before using the snapshot for model C.

# Transaction data schema

ExplainGuard-SMB reads an ordinary transaction export. One row per authorisation.

| Column | Type | Required | Meaning |
|---|---|---|---|
| `timestamp` | float (seconds) | yes | Time of the transaction (any epoch; must be sortable) |
| `merchant_id` | string | yes | Store / merchant account |
| `card_id` | string | yes | Card fingerprint or token (never a full card number) |
| `device_id` | string | yes | Device fingerprint from the checkout or processor |
| `ip_id` | string | yes | Network address or a hashed/truncated version of it |
| `amount` | float | yes | Amount in USD |
| `is_fraud` | 0/1 | for benchmarking | Final fraud label |
| `chargeback_time` | float (seconds) | for benchmarking | When the fraud label became known (blank if legit) |
| `txn_id` | string | optional | Transaction identifier |
| `fraud_type` | string | optional | Pattern label for per-pattern recall |

**Privacy:** use tokens or hashes for card, device and IP identifiers. The toolkit
only needs to know when two transactions share an identifier, not what it is.

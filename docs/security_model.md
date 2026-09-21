# Security Model

## Integrity
Messages are protected using HMAC-SHA256.

## Freshness
Replay attacks prevented via monotonic counters.

## Threat Model
- Tampered messages
- Replayed messages
- Invalid schema

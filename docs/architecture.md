# Architecture Overview

The secure-message-gateway follows a combined Top-Down and Bottom-Up design.

## Top-Down
- Message pipeline: validation → crypto → freshness → logging
- Deterministic behavior for safety-critical systems
- Extensible for REST API and monitoring dashboard

## Bottom-Up
- crypto.py: HMAC-SHA256
- freshness.py: monotonic counters
- logger.py: rotating audit logs
- gateway.py: orchestrates the pipeline

import csv
import json
from pathlib import Path

LOG_PATH = Path("logs/gateway.log")
OUT_PATH = Path("logs/export.csv")

def export_logs():
    with open(LOG_PATH, "r") as log, open(OUT_PATH, "w", newline="") as out:
        writer = csv.writer(out)
        writer.writerow(["timestamp", "event", "details"])

        for line in log:
            data = json.loads(line)

            timestamp = data.get("timestamp", "")
            event = data.get("event", "")
            payload = data.get("payload", {})

            # details = doar text, nu JSON complet
            if isinstance(payload, dict):
                details = "; ".join(f"{k}={v}" for k, v in payload.items())
            else:
                details = str(payload)

            writer.writerow([timestamp, event, details])

if __name__ == "__main__":
    export_logs()
    print("Logs exported to logs/export.csv")

import time
import json

# Get the current epoch time in seconds
def get_current_epoch_time() -> int:
    return int(time.time())


def size_bytes(data) -> int:
    # If it's not already a string, convert to JSON string
    if not isinstance(data, str):
        data = json.dumps(data, separators=(",", ":"))  # compact JSON

    return len(data.encode("utf-8"))
def scrub_secrets(obj):
    # Recursively remove any keys named 'api_key' or 'api_key_hash'
    if isinstance(obj, dict):
        return {
            k: scrub_secrets(v)
            for k, v in obj.items()
            if k not in ("api_key", "api_key_hash")
        }
    if isinstance(obj, list):
        return [scrub_secrets(i) for i in obj]
    return obj
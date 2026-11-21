ALLOWED_TOOLS = {"basic_memory_bm_search", "basic_memory_bm_read"}


def verify_inventory(events):
    contexts = [e for e in events if e["kind"] == "request.context"]
    snapshots = [e for e in events if e["kind"] == "request.context.snapshot"]
    if not contexts or not snapshots:
        raise ValueError("Missing live request context or inventory snapshot")
    if any(set(c.get("toolNames") or []) != ALLOWED_TOOLS for c in contexts):
        raise ValueError("Effective tool inventory must contain exactly bm_search and bm_read")
    for snapshot in snapshots:
        if set(snapshot.get("tools") or {}) != ALLOWED_TOOLS:
            raise ValueError("Snapshot contains an unexpected tool inventory")
        if not any(
            s["name"] == "basic_memory" and s["status"]["status"] == "connected" for s in snapshot["mcp"]["data"]
        ):
            raise ValueError("Basic Memory is not connected")
        if any(term in str(snapshot.get("system")) for term in ("answer-key", "prepare.py")):
            raise ValueError("System context references evaluation materials")
    return snapshots[0]

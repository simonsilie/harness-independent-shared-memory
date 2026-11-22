"""Technical approval gate for durable Basic Memory writes."""

ALLOWED_TOOLS = ("bm_project", "bm_read", "bm_search", "bm_write")


class ProposalError(ValueError):
    """An invalid or unusable approval proposal."""

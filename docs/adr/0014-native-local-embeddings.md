# Use native local embeddings for topic recall

Use Basic Memory's FastEmbed provider and hybrid search so topic queries can
find relevant notes phrased differently. This supersedes the text-only rollout
in [ADR 0007](0007-model-independent-storage-and-text-search.md), which still
defines Markdown as authoritative and embeddings as a rebuildable index.
Use text search for exact terms, metadata-only handover inventory and the
read-only recall experiment.

The runtime wheel carries the MCP project-creation patch. Historical text-only
checks can be reproduced from the revision recorded in the
[model-free operation report](../archive/model-free-operation.md).

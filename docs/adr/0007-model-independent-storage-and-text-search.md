# Keep storage and text search independent of AI models

Memory content must remain readable and usable when switching agents or language models, and storage and text search must work without an AI model or external AI service. Local embeddings may later improve semantic retrieval, but are optional and not required for the initial setup. Embeddings are rebuildable search indexes rather than authoritative knowledge; their absence must not prevent storage or text retrieval.

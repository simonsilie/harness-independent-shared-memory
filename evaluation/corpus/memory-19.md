---
title: "Embedding exception"
type: "note"
permalink: "memory-19"
id: "memory-19"
scope: "project"
project_id: "b9e8a625-31be-4bc8-8a1d-cb233ab53394"
review_status: "accepted"
source_uri: "../harness-independent-shared-memory.md"
source_revision: "sha256:49b0153bbf514d31ef42992dca88a37024506a1978f13f0a9c83b329f28953de"
source_section: "8"
---

# Embedding exception

The proposed phase 1A explicitly uses text query mode and permits local background embeddings as a documented exception to the no-inference target; configure no hosted embedding provider. Text queries alone do not disable indexing inference. Record the pinned release, actual provider/model, initial download, indexing time, and memory use. If no inference is mandatory, verify a supported configuration or choose another engine before starting. The exception ends at 1A: before 1B, demonstrate storage and keyword recall with inference disabled or unavailable, select an engine that can, or explicitly revise the requirement.

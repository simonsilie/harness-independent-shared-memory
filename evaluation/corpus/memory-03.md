---
title: "Canonical storage"
type: "note"
permalink: "memory-03"
id: "memory-03"
scope: "project"
project_id: "b9e8a625-31be-4bc8-8a1d-cb233ab53394"
review_status: "accepted"
source_uri: "../harness-independent-shared-memory.md"
source_revision: "sha256:49b0153bbf514d31ef42992dca88a37024506a1978f13f0a9c83b329f28953de"
source_section: "3"
---

# Canonical storage

The proposed architecture requires one canonical representation. Files and database rows must not be independently writable authorities. A database may index canonical Markdown records; document writes require atomic updates and revision checks.

---
title: "SQLite backup safety"
type: "note"
permalink: "memory-20"
id: "memory-20"
scope: "project"
project_id: "b9e8a625-31be-4bc8-8a1d-cb233ab53394"
review_status: "accepted"
source_uri: "../harness-independent-shared-memory.md"
source_revision: "sha256:49b0153bbf514d31ef42992dca88a37024506a1978f13f0a9c83b329f28953de"
source_section: "8"
---

# SQLite backup safety

The proposed deployment keeps SQLite on a local filesystem and uses supported consistent backups. Do not sync a live SQLite/WAL database or place it on a shared network filesystem. Sync completed backups or exported documents instead; document sync still requires conflict handling.

---
title: "Stale proposal approval"
type: "note"
permalink: "memory-14"
id: "memory-14"
scope: "project"
project_id: "b9e8a625-31be-4bc8-8a1d-cb233ab53394"
review_status: "accepted"
source_uri: "../harness-independent-shared-memory.md"
source_revision: "sha256:49b0153bbf514d31ef42992dca88a37024506a1978f13f0a9c83b329f28953de"
source_section: "7"
---

# Stale proposal approval

The proposed acceptance workflow requires a pending proposal and compares its original stored `base_revision` against the current durable revision. A mismatch must return a conflict and leave the proposal pending; obtain a new proposal against the current revision instead of changing the old proposal's base. For a new target, acceptance requires that no record already exists.

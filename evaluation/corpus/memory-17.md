---
title: "Read time expiry"
type: "note"
permalink: "memory-17"
id: "memory-17"
scope: "project"
project_id: "b9e8a625-31be-4bc8-8a1d-cb233ab53394"
review_status: "accepted"
source_uri: "../harness-independent-shared-memory.md"
source_revision: "sha256:49b0153bbf514d31ef42992dca88a37024506a1978f13f0a9c83b329f28953de"
source_section: "7"
---

# Read time expiry

The proposed lifecycle requires checking `expires_at` at read time, including cached and indexed results. Expiry must not depend on a cleanup job or destroy history. Completed handovers and superseded revisions must also be excluded from ordinary recall.

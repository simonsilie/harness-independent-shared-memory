---
title: "Write retries"
type: "note"
permalink: "memory-15"
id: "memory-15"
scope: "project"
project_id: "b9e8a625-31be-4bc8-8a1d-cb233ab53394"
review_status: "accepted"
source_uri: "../harness-independent-shared-memory.md"
source_revision: "sha256:49b0153bbf514d31ef42992dca88a37024506a1978f13f0a9c83b329f28953de"
source_section: "7"
---

# Write retries

The proposed write contract scopes idempotency keys to the authenticated caller and operation. A retry must return the original result; reuse with a different payload must fail. Retrying acceptance of an already accepted proposal must return its original resulting revision.

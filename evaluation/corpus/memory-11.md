---
title: "Review execution boundary"
type: "note"
permalink: "memory-11"
id: "memory-11"
scope: "project"
project_id: "b9e8a625-31be-4bc8-8a1d-cb233ab53394"
review_status: "accepted"
source_uri: "../harness-independent-shared-memory.md"
source_revision: "sha256:49b0153bbf514d31ef42992dca88a37024506a1978f13f0a9c83b329f28953de"
source_section: "6"
---

# Review execution boundary

The proposed enforcement boundary requires agents to lack reviewer credentials, unrestricted backend APIs, and shell write access to canonical files. A local stdio server running as the agent's OS user is insufficient by itself. The read-only experiment assumes a trusted owner; enforced capture and team deployment must protect these bypass paths.

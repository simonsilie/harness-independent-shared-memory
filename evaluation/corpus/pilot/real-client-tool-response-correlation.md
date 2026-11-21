---
title: Correlating real-client tool responses
type: note
permalink: main/pilot/real-client-tool-response-correlation
id: real-client-tool-response-correlation
scope: project
project_id: b9e8a625-31be-4bc8-8a1d-cb233ab53394
review_status: accepted
source_uri: ../../../AGENTS.md
source_revision: sha256:d5c21e0a1483bd9f7a532e424af3a2a664b3558adb20a86987a2548f212396ae
source_section: Session Learnings
embed: false
tags:
- opencode
- evaluation-harness
---

# Correlating real-client tool responses

In harness-independent-shared-memory real-client probes, match tool responses by call ID or exact arguments rather than transcript position. Parallel calls can complete out of order.

The protected eligibility probe observed OpenCode start the shared-token search first but complete the superseded-token search first. Matching responses by their arguments let the verifier revalidate the retained captures without repeating owner operations.

Sources:
- `AGENTS.md`, Session Learnings
- `evaluation/phase1b/eligibility_lifecycle.py`, response matching in `turn`
- `evaluation/phase1b/runs/20261116T113301.888339Z-real-clients/opencode-immediate-1.events.jsonl`: shared-token search start/end 1794829644936/1794829660232; superseded-token search start/end 1794829645994/1794829660230.

- relates_to [[OpenCode project config resolution]]

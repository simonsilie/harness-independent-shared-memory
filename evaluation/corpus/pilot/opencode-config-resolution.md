---
title: OpenCode project config resolution
type: note
permalink: opencode-config-resolution
id: opencode-config-resolution
scope: project
project_id: b9e8a625-31be-4bc8-8a1d-cb233ab53394
review_status: accepted
source_uri: ../../../AGENTS.md
source_revision: sha256:ffd71ecd9c48a4c8431bb017ea715a84f7b81b1686c8008e7d66471f9022befb
source_section: Session Learnings
tags:
- opencode
- evaluation-harness
---

# OpenCode project config resolution

OpenCode resolves a session's project configuration from the git project root, so a disposable
`.opencode/opencode.json` written into a run workspace is never discovered. Inject a disposable
configuration over the live one with the undocumented `OPENCODE_CONFIG_CONTENT` environment
variable (an inline JSON merge, analogous to `OPENCODE_CLI_CONFIG_CONTENT`), keeping the client
in the real checkout.

The experimental MCP connect endpoint
(`POST /api/experimental/mcp/{server}/connect?location[directory]=...`) only works after a first
`opencode run` has opened the location, which is why the harnesses run a readiness turn before
connecting. Exercised by `evaluation/opencode/run.py --outage`.

- relates_to [[Claude Code init tool inventory timing]]
- relates_to [[Independent Claude sessions inside Claude Code]]
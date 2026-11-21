---
title: Claude Code init tool inventory timing
type: note
permalink: claude-init-tool-inventory
id: claude-init-tool-inventory
scope: project
project_id: b9e8a625-31be-4bc8-8a1d-cb233ab53394
review_status: accepted
source_uri: ../../../AGENTS.md
source_revision: sha256:ffd71ecd9c48a4c8431bb017ea715a84f7b81b1686c8008e7d66471f9022befb
source_section: Session Learnings
tags:
- claude-code
- evaluation-harness
---

# Claude Code init tool inventory timing

Claude Code emits its `init` tool inventory only after a prompt is submitted. To capture the
inventory without a model request, add a `UserPromptSubmit` hook that exits 2: the hook blocks
the prompt, so the turn stops after the live inventory is reported and before any model call.

This is exercised by `evaluation/claude/run.py --verify-only`, whose preflight mode also blocks
the outage run the same way — which is why the Claude outage check records server status and
tools but never observes model behaviour without the server.

- relates_to [[OpenCode project config resolution]]

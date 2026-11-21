---
title: Independent Claude sessions inside Claude Code
type: note
permalink: independent-claude-session-variables
id: independent-claude-session-variables
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

# Independent Claude sessions inside Claude Code

When launching `claude` from inside a Claude Code session, strip the inherited
`CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_CHILD_SESSION`, `CLAUDE_CODE_SESSION_ATTENDED` and
`CLAUDE_CODE_MESSAGING_*` variables, otherwise the evaluated client attaches to the parent
session instead of running independently. `evaluation/claude/run.py` builds its environment
this way before every client run.

- relates_to [[OpenCode project config resolution]]

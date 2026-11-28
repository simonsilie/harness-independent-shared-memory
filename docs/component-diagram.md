# Component diagram

The repository extends Basic Memory with an approval gate, backup and export tools, and a separate evaluation environment.

```mermaid
flowchart TB
    Owner["Owner / terminal approval"]
    Clients["Coding agents<br/>Codex · OpenCode · Claude Code"]

    subgraph Repo["This repository"]
        Instructions["Instructions and rules<br/>Recall · handovers · archiving"]
        Gate["Approval gate<br/>MCP proxy"]
        Approval["Approval CLI<br/>shared_memory/approval_gate"]
        Ops["memory-ops<br/>Backup · restore · export"]
        Eval["Evaluation<br/>Corpus · questions · runners · scoring"]
        Tests["Tests"]
    end

    subgraph External["External components and data"]
        BM["Basic Memory<br/>MCP server and CLI"]
        Store[("Local store<br/>Markdown notes · SQLite · configuration")]
        Embed["FastEmbed<br/>local embeddings"]
        Backup[("Snapshots /<br/>portable OKF export")]
        TestStore[("Isolated<br/>test corpus")]
    end

    Instructions -. "guide behavior" .-> Clients
    Clients -- "MCP requests" --> Gate
    Gate -- "reads and eligible<br/>temporary writes" --> BM
    Gate -- "durable write proposal" --> Approval
    Owner -- "reviews and confirms" --> Approval
    Approval -- "approved write" --> BM
    BM <--> Store
    BM --> Embed
    Ops -- "backs up / restores" --> Store
    Ops -- "uses Basic Memory CLI<br/>for export" --> BM
    Ops --> Backup
    Eval -- "runs and verifies" --> Clients
    Eval -- "uses a separate<br/>Basic Memory store" --> TestStore
    Tests -. "test" .-> Gate
    Tests -. "test" .-> Ops
    Tests -. "test" .-> Eval
```

The evaluation uses a separate corpus to check client tool use, note retrieval and reads, and corpus integrity. See [Repository architecture](repository-architecture.md) for details.

import asyncio
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import yaml

ROOT = Path(__file__).resolve().parents[2]
if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
from evaluation.clients import behavior as b  # noqa: E402

INSTRUCTIONS = ROOT / "docs/shared-memory-lifecycle.md"


def snapshot(root):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*.md")}


def note(env, identifier):
    path = Path(env["BASIC_MEMORY_CONFIG_DIR"]).parent / ROOT.name / identifier
    content = path.read_text()
    metadata = yaml.safe_load(content.split("---", 2)[1])
    return metadata, content


async def call(session, out, label, tool, **args):
    result = await session.call_tool(tool, args | {"output_format": "json"})
    b.dump(out, label, result.model_dump(mode="json"))
    assert not result.is_error, result
    return json.loads("".join(block.text for block in result.content if block.type == "text"))


async def seed(env, tokens, out, now):
    with (out / "seed.stderr").open("a") as log:
        async with b.stdio_client(
            b.StdioServerParameters(command=b.SERVER[0], args=b.SERVER[1:], env=b.client_environment() | env),
            errlog=log,
        ) as streams:
            async with b.ClientSession(*streams) as session:
                await session.initialize()
                fixtures = {
                    "expired": ("active", now - timedelta(days=8), None),
                    "boundary": ("active", now - timedelta(days=7), None),
                    "extended": ("active", now - timedelta(days=8), now + timedelta(days=2)),
                    "extension-ended": ("active", now - timedelta(days=8), now - timedelta(seconds=1)),
                    "completed": ("completed", now, now + timedelta(days=2)),
                    "archived": ("archived", now, None),
                }
                for name, (status, activity, extension) in fixtures.items():
                    content = f'---\ntitle: Lifecycle {name}\nkind: temporary\nstatus: {status}\nlast_activity: "{activity.isoformat()}"\n'
                    if extension:
                        content += f'extended_until: "{extension.isoformat()}"\n'
                    content += f"---\nFortsetzungshinweis: {tokens[name]}. Quelle: isolierte Lifecycle-Prüfung.\n"
                    await call(
                        session,
                        out,
                        f"seed-{name}",
                        "bm_write",
                        project=ROOT.name,
                        identifier=f"temporary/{name}.md",
                        content=content,
                        overwrite=False,
                    )


async def conflict(env, out):
    params = b.StdioServerParameters(command=b.SERVER[0], args=b.SERVER[1:], env=b.client_environment() | env)
    with (out / "conflict.stderr").open("w") as log:
        async with b.stdio_client(params, errlog=log) as first, b.stdio_client(params, errlog=log) as second:
            async with b.ClientSession(*first) as a, b.ClientSession(*second) as c:
                await a.initialize()
                await c.initialize()
                args = {"project": ROOT.name, "identifier": "temporary/expired.md"}
                old_a = await call(a, out, "conflict-read-a", "bm_read", **args)
                old_c = await call(c, out, "conflict-read-b", "bm_read", **args)
                assert old_a["checksum"] == old_c["checksum"]
                content = old_a["content"] + "\nWinning temporary update."
                content = content.replace(
                    str(note(env, args["identifier"])[0]["last_activity"]), datetime.now(timezone.utc).isoformat()
                )
                await call(
                    a, out, "conflict-winner", "bm_write", **args, content=content, expected_checksum=old_a["checksum"]
                )
                saved = await call(a, out, "conflict-before-stale", "bm_read", **args)
                before = note(env, args["identifier"])[1]
                stale = await c.call_tool(
                    "bm_write",
                    args
                    | {
                        "content": old_c["content"] + "\nStale update.\n",
                        "expected_checksum": old_c["checksum"],
                        "output_format": "json",
                    },
                )
                b.dump(out, "conflict-stale", stale.model_dump(mode="json"))
                assert stale.is_error and "REVISION_CONFLICT" in str(stale), stale
                winner = await call(c, out, "conflict-preserved", "bm_read", **args)
                assert winner["checksum"] == saved["checksum"]
                assert winner["content"] == saved["content"]
                assert note(env, args["identifier"])[1] == before


def verify_updates(turns, env, started, now):
    writes = [args for calls, _ in turns for tool, args in calls if tool == "bm_write"]
    assert writes, turns
    for args in writes:
        assert args.get("expected_checksum"), args
    for args in (args for tool, args in turns[1][0] if tool == "bm_write"):
        metadata = yaml.safe_load(args["content"].split("---", 2)[1])
        assert datetime.fromisoformat(str(metadata["last_activity"])) >= started, metadata
    meta, text = note(env, "temporary/continuation.md")
    assert meta["status"] == "archived" and meta["archive_reason"] == "completed", meta
    assert "Ergebnisdatei" in text, text
    activity = datetime.fromisoformat(str(meta["last_activity"]).replace("Z", "+00:00"))
    assert started <= activity <= datetime.now(timezone.utc), meta
    extended, _ = note(env, "temporary/extended.md")
    assert datetime.fromisoformat(str(extended["extended_until"])) >= now + timedelta(days=13), extended
    restored, _ = note(env, "temporary/expired.md")
    assert restored["status"] == "active", restored
    assert all(
        restored.get(key) is None for key in ("archived_at", "archive_reason", "completed_at", "extended_until")
    ), restored
    assert datetime.fromisoformat(str(restored["last_activity"])) >= started, restored


async def main(out=None, clients=None):
    if out is None:
        out = Path(__file__).parent / "runs" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(mode=0o700, parents=True)
    now = datetime.now(timezone.utc)
    print(f"Lifecycle evidence: {out}", flush=True)
    before = snapshot(ROOT / "evaluation/corpus") | snapshot(Path.home() / "SharedMemory/notes")
    if clients is None:
        clients = ["codex", "opencode"]
    for client in clients:
        assert client in ("codex", "opencode"), client
        capture_out = out / client
        capture_out.mkdir()
        env = b.setup(capture_out, "store")
        tokens = {
            name: uuid4().hex
            for name in ("expired", "boundary", "extended", "extension-ended", "completed", "archived")
        }
        await seed(env, tokens, capture_out, now)
        token = uuid4().hex
        b.dump(capture_out, "fixture", {"tokens": tokens, "continuation_token": token, "environment": env})
        capture_prompts = [
            f"Wir unterbrechen den Abgleich Polarlicht. Als Nächstes ist die Ergebnisdatei zu prüfen. Die Fortsetzungskennung lautet {token}. Sichere das als temporäre Übergabe unter temporary/continuation.md für dieses Projekt, nicht als dauerhafte Erkenntnis."
        ]

        async def run(run_out, prompts):
            if client == "codex":
                return await b.codex(env, run_out, prompts, instructions=INSTRUCTIONS)
            return await asyncio.to_thread(b.opencode, env, run_out, prompts, instructions=INSTRUCTIONS)

        capture = await run(capture_out, capture_prompts)
        b.dump(capture_out, "capture", capture)
        meta, body = note(env, "temporary/continuation.md")
        assert meta["kind"] == "temporary" and meta["status"] == "active" and token in body, (meta, body)
        resume_out = out / f"{client}-resume"
        resume_out.mkdir()
        resume_prompts = [
            "Weiter mit Polarlicht: Wo haben wir aufgehört, was ist als Nächstes zu tun und welche Fortsetzungskennung gilt? Welche weiteren aktiven Lifecycle-Fortsetzungshinweise gibt es? Nenne Quellen.",
            "Die Vorprüfung ist erledigt; als Nächstes folgt die Prüfung der Ergebnisdatei. Aktualisiere die bestehende temporäre Polarlicht-Übergabe.",
            f"Verlängere die Verfügbarkeit der temporären Übergabe temporary/extended.md ausdrücklich bis {(now + timedelta(days=14)).isoformat()}.",
            "Polarlicht ist jetzt vollständig abgeschlossen. Aktualisiere die Übergabe entsprechend.",
            "Suche ausdrücklich im Archiv dieses Projekts nach temporary/expired.md und nenne den dortigen Fortsetzungshinweis mit Quelle.",
            "Stelle genau diesen archivierten Eintrag temporary/expired.md wieder für aktive Verwendung her.",
        ]
        started = datetime.now(timezone.utc)
        turns = await run(resume_out, resume_prompts)
        calls, answer = turns[0]
        assert token in answer and tokens["extended"] in answer, answer
        assert all(t not in answer for name, t in tokens.items() if name != "extended"), answer
        assert any(tool == "bm_read" for tool, _ in calls), calls
        assert tokens["expired"] in turns[4][1], turns[4]
        assert not any(
            tool == "bm_write" and args.get("identifier") in ("temporary/continuation.md", "temporary/extended.md")
            for tool, args in calls
        ), calls
        verify_updates(turns, env, started, now)
        for name in ("boundary", "extension-ended", "completed"):
            meta, _ = note(env, f"temporary/{name}.md")
            assert meta["status"] == "archived", (name, meta)
        await conflict(env, resume_out)
        assert len(list((Path(env["BASIC_MEMORY_CONFIG_DIR"]).parent / ROOT.name).rglob("*.md"))) == 7
        b.dump(
            resume_out,
            "verified",
            {
                "capture_fresh_session_resume": True,
                "expiry_completion_extension": True,
                "explicit_archive_restore": True,
                "temporary_revision_conflict": True,
                "retained_notes": 7,
            },
        )
        print(f"{client}: lifecycle verified", flush=True)
    assert before == snapshot(ROOT / "evaluation/corpus") | snapshot(Path.home() / "SharedMemory/notes")
    b.dump(
        out,
        "result",
        {
            "clients_passed": clients,
            "productive_notes_and_corpus_unchanged": True,
            "instructions": "candidate injected for verification; global activation separate",
        },
    )


if __name__ == "__main__":
    asyncio.run(main(clients=sys.argv[1:] or None))

---
title: Basic Memory generated columns
type: note
permalink: main/pilot/basic-memory-generated-columns
id: basic-memory-generated-columns
scope: project
project_id: b9e8a625-31be-4bc8-8a1d-cb233ab53394
review_status: accepted
source_uri: ../../../workflow/integration.py
source_revision: sha256:0ef01d72c3a529fb7c79c1b5d22ecfbcdb0d64d4bc623f83dfe00b26d8362b76
source_section: native_export / restore_native / _generated_columns
tags:
- basic-memory
- schema
- export
- restore
---

# Basic Memory generated columns

Nativtabellen von Basic Memory 1.0.0 enthalten SQLite-generierte Spalten
(`entity.tags_json`, `entity.frontmatter_status`, `entity.frontmatter_type`).
Ein zeilenweiser Export via `SELECT *` plus `INSERT` scheitert deshalb mit
„cannot INSERT into generated column". Generierte Spalten vor dem Export und
vor dem Einfügen über `PRAGMA table_xinfo` anhand des `hidden`-Flags
(`hidden != 0` = generiert) herausfiltern; sie sind abgeleiteter Zustand und
werden aus den Trägerspalten neu berechnet.

Im Projekt `harness-independent-shared-memory` beschränkt
`workflow/integration.py` diese Kopplung auf `native_export`, `restore_native`
und `_generated_columns`: der logische Workflow-Bundle-Export (Version 3) trägt
nur beschreibbare Spalten, der Restore lehnt unbekannte Spalten laut ab und
setzt außerdem `entity.vector_sync_deferred_at` auf NULL, weil semantische
Vektorzustände nicht mitrestauriert werden.

Zweitens erzeugt der native Initialisierungs-/Migrationspfad
(`ConfigManager`/ORM-Lese) die in `config.json` konfigurierten
Projektverzeichnisse vorab. Restore-Schritte, die dieselben Verzeichnisse mit
kanonischen Noten füllen, müssen deshalb `exist_ok=True` verwenden.

- relates_to [[Basic Memory restore path binding]]
- relates_to [[SQLite backup safety]]

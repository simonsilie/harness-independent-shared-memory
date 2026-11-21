---
title: Basic Memory restore path binding
type: note
permalink: main/pilot/basic-memory-restore-path-binding
id: basic-memory-restore-path-binding
scope: project
project_id: b9e8a625-31be-4bc8-8a1d-cb233ab53394
review_status: accepted
source_uri: ../../../evaluation/phase1b/run.py
source_revision: sha256:b2ea04a8eee1c4d510ceb60eaa3caab70107471a855da5e1982ebb002895ff5c
source_section: Backup and restore probe (lines 232–294)
tags:
- basic-memory
- restore
- evaluation-harness
---

# Basic Memory restore path binding

Bei Basic-Memory-Restores in einen anderen Pfad die kopierte Datenbank mit
`project move <Projekt> <neuer Korpuspfad>` neu binden, `project.path` in der
Datenbank prüfen und den Ursprungspfad während des Tests unerreichbar machen.
Eine geänderte Konfiguration allein genügt nicht, um die in der kopierten
Datenbank gespeicherte Projektpfadbindung zu aktualisieren.

Im Projekt `harness-independent-shared-memory` verschiebt die Restore-Probe in
`evaluation/phase1b/run.py` den Ursprungskorpus, setzt die Restore-Konfiguration,
führt `project move` aus und prüft den neuen Pfad per SQL. Anschließend prüft sie
nach vollständigem Suchindex-Neuaufbau den gelesenen Inhalt, erhaltene IDs und
Probe-Historie sowie die Suchergebnisse. Abschließend stellt sie sicher, dass
der Ursprungskorpus nicht neu angelegt wurde.

- relates_to [[SQLite backup safety]]

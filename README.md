# LIMS Core & Quality Management Simulator

Eksamensprojekt i Programmering (2026-11, s263aPRV1hfek1).  
En Python-baseret simulator af et Laboratory Information Management System (LIMS) målrettet kvalitetskontrol (QC) og laboratorie-support.

## Funktioner (CRUD & Automatisering)
* **Create:** Automatisk ID-generering (`TYPE-YYYYMMDD-XXX`) og kategorispecifik testtildeling for **RM**, **DS**, **DP** og **IHR**.
* **Read:** Interaktivt laboratorieoverblik med 4 sorterings- og filtreringsmuligheder (kronologisk, kritiske fejl først, uafsluttede opgaver og historisk arkiv).
* **Update:** Brugervenlig indtastning af resultater med formatvejledning, automatisk specifikationstjek (OOS-detektering), to-komponent spektrofotometrisk CSV-import samt automatisk oprettelse af retest-prøver (`-R1`).
* **Delete:** Fjernelse af specifikke analyseopsætninger fra en prøve.
* **Export & Persistens:** Relationel datalagring via indbygget SQLite-database samt eksport af filtrerede KPI-rapporter til CSV.

## Projektstruktur
* `main.py` – Applikationens startpunkt, menu-loop (`match-case`), exception handling, CSV-I/O og SQLite-integration.
* `lims_core.py` – Domæneklasser (`Analysis`, `SpectroAnalysis`, `Sample`) med indkapsling (`@property`), arv og composition.
* `lims_enums.py` – Enums for prøvetyper og statusser (`SampleType`, `SampleStatus`, `AnalysisStatus`).
* `hplc_output.csv` – Eksempelfil til demonstration af direkte instrument-import i menuvalg 3.

## Sådan køres programmet
1. Sørg for at **Python 3.10+** er installeret (kræves pga. `match-case`).
2. Klon eller download dette repository.
3. Kør `main.py` fra din terminal eller IDE (PyCharm / VS Code):
   ```bash
   python main.py
   ```

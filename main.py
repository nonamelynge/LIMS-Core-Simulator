import sqlite3
import os
import csv
import datetime
from lims_enums import AnalysisStatus, SampleStatus, SampleType
from lims_core import Analysis, SpectroAnalysis, Sample

SAMPLE_DATABASE = []
DB_FILE = "lims_database.db"

def init_sql_database():
    """Opretter SQLite database-tabeller med relationelle Foreign Keys."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS samples (
        sample_id TEXT PRIMARY KEY,
        sample_type TEXT NOT NULL,
        status TEXT NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sample_id TEXT NOT NULL,
        name TEXT NOT NULL,
        lower_limit REAL NOT NULL,
        upper_limit REAL NOT NULL,
        result REAL,
        status TEXT NOT NULL,
        expected_wavelength INTEGER,
        measured_wavelength INTEGER,
        FOREIGN KEY (sample_id) REFERENCES samples (sample_id) ON DELETE CASCADE
    );
    """)
    conn.commit()
    conn.close()

def save_data_to_sql():
    """Synkroniserer det objektorienterede hierarki ned i SQL-databasen."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analyses;")
        cursor.execute("DELETE FROM samples;")
        
        for sample in SAMPLE_DATABASE:
            cursor.execute(
                "INSERT INTO samples (sample_id, sample_type, status) VALUES (?, ?, ?);",
                (sample.sample_id, sample.sample_type.name, sample.status.value)
            )
            for ana in sample.analyses:
                is_spectro = isinstance(ana, SpectroAnalysis)
                exp_wave = ana.expected_wavelength if is_spectro else None
                meas_wave = ana.measured_wavelength if is_spectro else None
                
                cursor.execute("""
                INSERT INTO analyses (sample_id, name, lower_limit, upper_limit, result, status, expected_wavelength, measured_wavelength) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (sample.sample_id, ana.name, ana.lower_limit, ana.upper_limit, ana.result, ana.status.value, exp_wave, meas_wave))
                
        conn.commit()
        conn.close()
        print(f"\n[SQL SYSTEM] Alle data blev synkroniseret og gemt i '{DB_FILE}'!")
    except Exception as e:
        print(f"\n[SQL FEJL] Kunne ikke gemme til database: {e}")

def load_data_from_sql():
    """Henter data fra SQL-tabellerne og genopbygger OOP-objektstrukturen."""
    try:
        if not os.path.exists(DB_FILE):
            return
            
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT sample_id, sample_type, status FROM samples;")
        db_samples = cursor.fetchall()
        
        for s_row in db_samples:
            s_id, s_type_name, s_status = s_row
            sample = Sample(s_id, SampleType[s_type_name])
            sample.analyses = []
            sample.status = SampleStatus(s_status)
            
            cursor.execute("SELECT name, lower_limit, upper_limit, result, status, expected_wavelength, measured_wavelength FROM analyses WHERE sample_id = ?;", (s_id,))
            for a_row in cursor.fetchall():
                a_name, lower, upper, result, a_status, exp_wave, meas_wave = a_row
                if exp_wave is not None:
                    ana = SpectroAnalysis(a_name, lower, upper, exp_wave)
                    ana.measured_wavelength = meas_wave
                else:
                    ana = Analysis(a_name, lower, upper)
                
                if result is not None:
                    ana._result = result
                ana.status = AnalysisStatus(a_status)
                sample.analyses.append(ana)
                
            SAMPLE_DATABASE.append(sample)
        conn.close()
        print(f"[SQL SYSTEM] Eksisterende relationelle data indlæst korrekt.")
    except Exception as e:
        print(f"[SQL FEJL] Fejl under indlæsning: {e}")
def generate_automatic_sample_id(stype_name: str) -> str:
    today_str = datetime.datetime.now().strftime("%Y%m%d")
    prefix = f"{stype_name}-{today_str}-"
    counter = 1
    for sample in SAMPLE_DATABASE:
        if sample.sample_id.startswith(prefix) and not "-R" in sample.sample_id:
            counter += 1
    return f"{prefix}{counter:03d}"

def read_instrument_csv(file_path: str) -> tuple:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Filen '{file_path}' blev ikke fundet.")
    with open(file_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames:
            cleaned_fields = [field.strip().lower() for field in reader.fieldnames]
        else:
            raise ValueError("CSV-filen mangler kolonneoverskrifter.")
        if "wavelength" not in cleaned_fields or "concentration" not in cleaned_fields:
            raise KeyError("CSV-filen skal indeholde kolonnerne 'Wavelength' og 'Concentration'.")
        for row in reader:
            row_cleaned = {k.strip().lower(): v for k, v in row.items() if k}
            return int(row_cleaned["wavelength"]), float(row_cleaned["concentration"])
    raise ValueError("CSV-filen indeholdt ingen rækker med data.")

def trigger_automatic_retest(failed_sample: Sample):
    print("\n--- AUTOMATISK RETEST LOGIK (OOS HANDLING) ---")
    svar = input(f"Prøve {failed_sample.sample_id} er REJECTED pga. OOS. Vil du oprette en Retest-prøve? (ja/nej): ").strip().lower()
    if svar in ["ja", "j"]:
        base_id = failed_sample.sample_id.split("-R")[0]
        retest_count = sum(1 for s in SAMPLE_DATABASE if s.sample_id.startswith(base_id) and "-R" in s.sample_id) + 1
        retest_id = f"{base_id}-R{retest_count}"
        retest_sample = Sample(retest_id, failed_sample.sample_type)
        retest_sample.analyses = []
        for ana in failed_sample.analyses:
            if isinstance(ana, SpectroAnalysis):
                retest_sample.add_analysis(SpectroAnalysis(ana.name, ana.lower_limit, ana.upper_limit, ana.expected_wavelength))
            else:
                retest_sample.add_analysis(Analysis(ana.name, ana.lower_limit, ana.upper_limit, ana.decimals))
        SAMPLE_DATABASE.append(retest_sample)
        print(f"[SUCCES] Automatisk Retest-prøve oprettet med ID: {retest_id}")
    else:
        print("[INFO] Retest afvist af laboranten.")

def main():
    init_sql_database()
    load_data_from_sql()
    
    while True:
        print("\n========================================================")
        print("     LIMS CORE SYSTEM v2.0 - QUALITY MANAGEMENT         ")
        print("========================================================")
        print("1. [CREATE] Registrer og generer ny prøve automatisk")
        print("2. [READ]   Vis laboratorieoverblik (SQL datagrundlag)")
        print("3. [UPDATE] Indtast måling eller indlæs instrument-CSV")
        print("4. [DELETE] Slet en analyseopsætning fra en prøve")
        print("5. [EXPORT] Generer ledelses- og KPI-rapporter (CSV)")
        print("6. [EXIT]   Gem ændringer til SQL og luk systemet")
        print("========================================================")
        
        valg = input("Vælg funktion (1-6): ").strip()

        match valg:
            case "1":
                print("\n--- REGISTRER NY PRØVE (Automatisk ID generering) ---")
                print("Vælg prøvetype:")
                print("1. RM  (Raw Material)     [Krav: pH, Renhed]")
                print("2. DS  (Drug Substance)   [Krav: pH, Renhed, UV-Vis]")
                print("3. DP  (Drug Product)     [Krav: Renhed, UV-Vis]")
                print("4. IHR (In House Reference) [Krav: Alle analyser]")
                
                type_valg = input("Vælg type (1-4): ").strip()
                type_map = {"1": SampleType.RM, "2": SampleType.DS, "3": SampleType.DP, "4": SampleType.IHR}
                
                if type_valg not in type_map:
                    print("[VALIDERINGFEJL] Ugyldigt valg af prøvetype. Afbryder.")
                    continue
                    
                valgt_type = type_map[type_valg]
                auto_id = generate_automatic_sample_id(valgt_type.name)
                
                ny_prøve = Sample(auto_id, valgt_type)
                SAMPLE_DATABASE.append(ny_prøve)
                print(f"\n[SUCCES] Prøve oprettet med ID: {auto_id}")
                print(f"Kategori-specifikt testprogram tildelt automatisk for {valgt_type.value}.")

            case "2":
                print("\n--- LAB DATABASE OVERBLIK (Read) ---")
                if not SAMPLE_DATABASE:
                    print("LIMS-databasen er tom.")
                    continue
                
                print("Visnings- og sorteringsmuligheder:")
                print("1. Sorter kronologisk efter Sample ID (Vis alle)")
                print("2. Sorter kritiske prøver først (Rejected/OOS øverst)")
                print("3. Vis KUN uafsluttede prøver (Pending / In Progress)")
                print("4. Vis KUN afsluttede prøver (Approved / Rejected)")
                s_valg = input("Vælg mulighed (1-4): ").strip()
                
                prøver_der_skal_vises = list(SAMPLE_DATABASE)
                
                if s_valg == "2":
                    status_prioritet = {SampleStatus.REJECTED: 0, SampleStatus.IN_PROGRESS: 1, SampleStatus.REGISTERED: 2, SampleStatus.APPROVED: 3}
                    prøver_der_skal_vises.sort(key=lambda x: status_prioritet.get(x.status, 99))
                elif s_valg == "3":
                    prøver_der_skal_vises = [s for s in SAMPLE_DATABASE if s.status in [SampleStatus.REGISTERED, SampleStatus.IN_PROGRESS]]
                    if not prøver_der_skal_vises:
                        print("\n[INFO] Der er ingen uafsluttede testopgaver i laboratoriet. Alt er Passed/Approved!")
                        continue
                elif s_valg == "4":
                    prøver_der_skal_vises = [s for s in SAMPLE_DATABASE if s.status in [SampleStatus.APPROVED, SampleStatus.REJECTED]]
                    if not prøver_der_skal_vises:
                        print("\n[INFO] Der er endnu ingen afsluttede eller færdigbehandlede prøver i systemet.")
                        continue
                else:
                    prøver_der_skal_vises.sort(key=lambda x: x.sample_id)
                
                for sample in prøver_der_skal_vises:
                    sample.sort_analyses()
                    print(f"\nPRØVE-ID: {sample.sample_id} | Kategori: {sample.sample_type.value} | Status: [{sample.status.value}]")
                    for ana in sample.analyses:
                        if isinstance(ana, SpectroAnalysis):
                            wave_info = f" (A_max: {ana.measured_wavelength if ana.measured_wavelength else 'Pending'} nm / Target: {ana.expected_wavelength} nm)"
                            res_str = f"{ana.result:.3f} %" if ana.result is not None else "Ikke analyseret"
                            print(f"  └── Test: {ana.name + wave_info:<40} Spec: [{ana.lower_limit:.3f} - {ana.upper_limit:.3f} %] | Res: {res_str:<12} | Status: {ana.status.value}")
                        else:
                            res_str = f"{ana.result:.{ana.decimals}f}" if ana.result is not None else "Ikke analyseret"
                            print(f"  └── Test: {ana.name:<40} Spec: [{ana.lower_limit} - {ana.upper_limit}] | Res: {res_str:<12} | Status: {ana.status.value}")
            case "3":
                print("\n--- INDLÆS ANALYSERESULTAT (Update) ---")
                aktive_prøver = [s for s in SAMPLE_DATABASE if s.status not in [SampleStatus.APPROVED, SampleStatus.REJECTED]]
                
                if not aktive_prøver:
                    print("[INFO] Der er ingen aktive eller uafsluttede prøver at indtaste resultater for lige nu.")
                    continue

                print("Vælg en aktiv prøve fra listen:")
                for i, s in enumerate(aktive_prøver):
                    print(f"{i+1}. {s.sample_id} ({s.sample_type.value}) - Status: [{s.status.value}]")
                
                try:
                    s_idx = int(input("Indtast nummer på prøven: ")) - 1
                    if s_idx < 0 or s_idx >= len(aktive_prøver):
                        print("[VALIDERINGSFEJL] Prøven findes ikke.")
                        continue
                    
                    sample = aktive_prøver[s_idx]
                    print(f"\nDu har valgt prøve: {sample.sample_id}")

                    print("\nVælg den analyse, der skal opdateres:")
                    for i, ana in enumerate(sample.analyses):
                        type_str = "Spektrofotometrisk (2-komp)" if isinstance(ana, SpectroAnalysis) else "Standard"
                        print(f"{i+1}. {ana.name:<12} [Type: {type_str}] (Status: {ana.status.value})")

                    idx = int(input("Vælg nummer på analysen: ")) - 1
                    if idx < 0 or idx >= len(sample.analyses):
                        print("[VALIDERINGSFEJL] Nummeret findes ikke.")
                        continue

                    valgt_ana = sample.analyses[idx]

                    if isinstance(valgt_ana, SpectroAnalysis):
                        print(f"\n--- SPEKTROFOTOMETRI EVALUERING (Target: {valgt_ana.expected_wavelength} nm) ---")
                        print("1. Manuel indtastning")
                        print("2. Indlæs instrument-CSV fil")
                        metode = input("Vælg metode (1-2): ").strip()

                        if metode == "2":
                            filnavn = input("Indtast stien/navnet på instrument-CSV-filen (f.eks. hplc_output.csv): ").strip()
                            wave_in, conc_in = read_instrument_csv(filnavn)
                            valgt_ana.measured_wavelength = wave_in
                            værdi = conc_in
                            print(f"[FILINDSIGT] Komponent 1 (Wavelength): {wave_in} nm | Komponent 2 (Koncentration): {conc_in} %")
                        else:
                            valgt_ana.measured_wavelength = int(input("Indtast Komponent 1: Bølgelængde for max absorbans i nm (f.eks. 540): "))
                            print(f"Indtast Komponent 2: Koncentration i % (Godkendt interval: {valgt_ana.lower_limit} - {valgt_ana.upper_limit} %)")
                            værdi = float(input("Indtast værdi (fx 95.123): "))
                    else:
                        print(f"\nIndtast resultat for {valgt_ana.name} (Godkendt interval: {valgt_ana.lower_limit} - {valgt_ana.upper_limit})")
                        if valgt_ana.decimals == 1:
                            værdi = float(input("Indtast værdi (fx 99.1): "))
                        elif valgt_ana.decimals == 2:
                            værdi = float(input("Indtast værdi (fx 7.15): "))
                        else:
                            værdi = float(input(f"Indtast værdi ({valgt_ana.decimals} decimaler): "))

                    valgt_ana.result = værdi
                    sample.evaluate_sample()
                    print(f"\n[SUCCES] Resultater registreret! Analyse-status opdateret til: {valgt_ana.status.value}")

                    if valgt_ana.status == AnalysisStatus.OOS:
                        print("⚠️ [KVALITETSADVARSEL] Målingen er uden for specifikation (OOS)!")
                        trigger_automatic_retest(sample)

                except (ValueError, IndexError, KeyError, FileNotFoundError) as error:
                    print(f"[VALIDERINGSFEJL/FEJL] Handling afbrudt. Årsag: {error}")

            case "4":
                print("\n--- SLET ANALYSE FRA PRØVE (Delete) ---")
                if not SAMPLE_DATABASE:
                    print("[INFO] Der er ingen prøver i systemet.")
                    continue

                for i, s in enumerate(SAMPLE_DATABASE):
                    print(f"{i+1}. {s.sample_id}")

                try:
                    s_idx = int(input("Indtast nummer på prøven: ")) - 1
                    if s_idx < 0 or s_idx >= len(SAMPLE_DATABASE):
                        print("[VALIDERINGSFEJL] Nummeret findes ikke.")
                        continue

                    sample = SAMPLE_DATABASE[s_idx]
                    ana_navn = input(f"Indtast navnet på analysen, der skal fjernes fra {sample.sample_id}: ").strip()

                    if sample.remove_analysis(ana_navn):
                        print(f"[SUCCES] '{ana_navn}' blev slettet fra {sample.sample_id} i hukommelsen. Gem for at opdatere SQL.")
                    else:
                        print(f"[FEJL] Testen '{ana_navn}' blev ikke fundet på denne prøve.")
                except ValueError:
                    print("[VALIDERINGSFEJL] Input skal være et tal.")

            case "5":
                print("\n--- GENERER LEDELSES- OG KPI-RAPPORTER (CSV Eksport) ---")
                if not SAMPLE_DATABASE:
                    print("[INFO] Databasen er tom. Ingen data at eksportere.")
                    continue

                print("Hvilken rapporttype ønsker du at udtrække til CSV?")
                print("1. Komplet databaseudtræk (Alle registrerede prøver)")
                print("2. Kritiske afvigelser (Kun Rejected/OOS prøver)")
                print("3. Ugeskema / To-Do liste (Kun uafsluttede opgaver)")
                print("4. Historisk Arkivtræk (Kun afsluttede prøver)")

                r_valg = input("Vælg rapport (1-4): ").strip()

                prøver_til_export = list(SAMPLE_DATABASE)
                filnavn = "lims_export_alle.csv"

                if r_valg == "2":
                    prøver_til_export = [s for s in SAMPLE_DATABASE if s.status == SampleStatus.REJECTED]
                    filnavn = "lims_export_kritiske.csv"
                elif r_valg == "3":
                    prøver_til_export = [s for s in SAMPLE_DATABASE if s.status in [SampleStatus.REGISTERED, SampleStatus.IN_PROGRESS]]
                    filnavn = "lims_export_todo.csv"
                elif r_valg == "4":
                    prøver_til_export = [s for s in SAMPLE_DATABASE if s.status in [SampleStatus.APPROVED, SampleStatus.REJECTED]]
                    filnavn = "lims_export_arkiv.csv"

                if not prøver_til_export:
                    print("[INFO] Der blev ikke fundet data, som matcher det valgte filter. Ingen CSV oprettet.")
                    continue

                try:
                    with open(filnavn, mode="w", newline="", encoding="utf-8") as file:
                        writer = csv.writer(file)
                        writer.writerow(["SampleID", "SampleType", "SampleStatus", "AnalysisName", "LowerLimit", "UpperLimit", "Result", "AnalysisStatus", "MeasuredWavelength"])
                        for sample in prøver_til_export:
                            for ana in sample.analyses:
                                meas_wave = ana.measured_wavelength if isinstance(ana, SpectroAnalysis) else ""
                                writer.writerow([
                                    sample.sample_id, sample.sample_type.value, sample.status.value,
                                    ana.name, ana.lower_limit, ana.upper_limit,
                                    ana.result if ana.result is not None else "", ana.status.value, meas_wave
                                ])
                    print(f"\n[EKSPORT SUCCES] Filen '{filnavn}' er genereret i dit PyCharm/VS Code projekt!")
                except Exception as e:
                    print(f"[EKSPORT FEJL] Kunne ikke oprette CSV-rapport: {e}")

            case "6":
                save_data_to_sql()
                print("\n[SYSTEM] Lukker LIMS Core. Data er sikkert synkroniseret med din SQL database. God arbejdslyst!")
                break

            case _:
                print("[VALIDERINGSFEJL] Ugyldigt input. Vælg et tal mellem 1 og 6.")

if __name__ == "__main__":
    main()

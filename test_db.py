import sqlite3
import traceback

with open("db_patch_log.txt", "w") as f:
    f.write("Checking DB...\n")
    try:
        conn = sqlite3.connect('db.sqlite3')
        cursor = conn.cursor()
        
        # Check patient_consultationrecord
        cursor.execute('PRAGMA table_info(patient_consultationrecord)')
        columns = [row[1] for row in cursor.fetchall()]
        f.write(f"Consultation columns: {columns}\n")
        
        if "diagnosis_text" not in columns:
            f.write("adding diagnosis_text...\n")
            cursor.execute("ALTER TABLE patient_consultationrecord ADD COLUMN diagnosis_text varchar(255) NULL")
            f.write("Added!\n")
        
        # Check patient_symptom
        cursor.execute('PRAGMA table_info(patient_symptom)')
        sym_cols = [row[1] for row in cursor.fetchall()]
        f.write(f"Symptom columns: {sym_cols}\n")
        
        if "doctor_modified_diagnosis_text" not in sym_cols:
            f.write("adding doctor_modified_diagnosis_text...\n")
            cursor.execute("ALTER TABLE patient_symptom ADD COLUMN doctor_modified_diagnosis_text text NULL")
            f.write("Added!\n")
            
        conn.commit()
        conn.close()
        f.write("Done\n")
    except Exception as e:
        f.write(traceback.format_exc())

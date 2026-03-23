import sqlite3, sys
db = sqlite3.connect('db.sqlite3')
cur = db.cursor()
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
with open('db_check_result.txt', 'w') as f:
    f.write("Tables:\n" + "\n".join(sorted(tables)) + "\n")
    f.write("\nadmin_panel_adminuser exists: " + str('admin_panel_adminuser' in tables) + "\n")
db.close()
print("Done")

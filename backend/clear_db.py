import os
import sqlite3

db_path = None
for root, dirs, files in os.walk('.'):
    if 'farm_memory.db' in files:
        db_path = os.path.join(root, 'farm_memory.db')
        break

if not db_path:
    print('Could not find farm_memory.db in the current folder or subfolders.')
else:
    print(f'Found DB at: {db_path}')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    tables = [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    print(f'Tables found: {tables}')
    
    for table in tables:
        if table != 'farmers':
            conn.execute(f"DELETE FROM {table};")
            print(f'Cleared table: {table}')
            
    conn.commit()
    conn.close()
    print('Call history cleared successfully!')

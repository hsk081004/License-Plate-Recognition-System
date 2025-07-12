import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# List all tables
tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("📋 Tables found:", tables)

# Check content of history table
try:
    history = cursor.execute("SELECT * FROM history").fetchall()
    print("🧾 History table contents:", history)
except sqlite3.OperationalError as e:
    print("⚠️ Error reading 'history' table:", e)

conn.close()

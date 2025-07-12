import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    cur = conn.cursor()

    # Create users table (if not exists)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')

    # Create history table (if not exists)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            image_path TEXT NOT NULL,
            plate_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert default admin user if not exists
    cur.execute('''
        INSERT OR IGNORE INTO users (username, password)
        VALUES (?, ?)
    ''', ("admin", "admin123"))

    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("✅ Creating tables...")
    init_db()
    print("🎉 Database initialized successfully.")

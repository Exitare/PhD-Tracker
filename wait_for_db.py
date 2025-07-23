# wait_for_db.py

import time
import pymysql
import os

host = os.getenv("DB_HOST", "db")
port = int(os.getenv("DB_PORT", 3306))
user = os.getenv("DB_USER", "root")
password = os.getenv("DB_PASSWORD", "")
max_tries = 30

for i in range(max_tries):
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=password)
        conn.close()
        print("✅ DB is ready.")
        break
    except Exception as e:
        print(f"⏳ Waiting for DB... ({i+1}/{max_tries})")
        time.sleep(2)
else:
    raise Exception("❌ DB not ready after waiting.")
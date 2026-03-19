import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.services.scheduler import init_scheduler
from sqlalchemy import text

app = create_app()

# 启用SQLite WAL模式
with app.app_context():
    with db.engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.commit()

scheduler = init_scheduler(app)

if __name__ == "__main__":
    print("=" * 50)
    print("  KSQC backend server starting")
    print("  URL: http://0.0.0.0:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=False)

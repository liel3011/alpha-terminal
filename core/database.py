import os
import sqlite3
import pandas as pd
from datetime import datetime
import base64

class DatabaseManager:
    def __init__(self, db_path="data/journal.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        # טבלה חדשה שתומכת בשמירת תמונה מקודדת
        conn.execute('''CREATE TABLE IF NOT EXISTS trade_journal_v2 
                        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                         timestamp TEXT, 
                         ticker TEXT, 
                         entry REAL, 
                         atr_sl REAL, 
                         notes TEXT,
                         image_data TEXT)''')
        conn.commit()
        conn.close()

    def _encode_image(self, image_path):
        """ממיר תמונה לטקסט (Base64) כדי לשמור בבסיס הנתונים לנצח"""
        if not image_path or not os.path.exists(image_path):
            return ""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception:
            return ""

    def log_trade(self, ticker, entry, atr_sl, notes, image_path=None):
        encoded_img = self._encode_image(image_path)
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT INTO trade_journal_v2 (timestamp, ticker, entry, atr_sl, notes, image_data) VALUES (?, ?, ?, ?, ?, ?)",
                     (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ticker, entry, atr_sl, notes, encoded_img))
        conn.commit()
        conn.close()

    def get_journal_data(self):
        conn = sqlite3.connect(self.db_path)
        try:
            df = pd.read_sql_query("SELECT id, timestamp, ticker, entry, atr_sl, notes, image_data FROM trade_journal_v2 ORDER BY timestamp DESC", conn)
        except Exception:
            df = pd.DataFrame()
        conn.close()
        return df

    def delete_trade(self, trade_id):
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM trade_journal_v2 WHERE id = ?", (trade_id,))
        conn.commit()
        conn.close()

    def update_notes(self, trade_id, new_notes):
        conn = sqlite3.connect(self.db_path)
        conn.execute("UPDATE trade_journal_v2 SET notes = ? WHERE id = ?", (new_notes, trade_id))
        conn.commit()
        conn.close()
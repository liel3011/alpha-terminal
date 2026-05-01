import os
import base64
import pandas as pd
import streamlit as st
from supabase import create_client, Client

class DatabaseManager:
    def __init__(self):
        """
        Initializes the Supabase client using credentials stored in 
        Streamlit Secrets (Advanced Settings).
        """
        try:
            self.url = st.secrets["SUPABASE_URL"]
            self.key = st.secrets["SUPABASE_KEY"]
            self.supabase: Client = create_client(self.url, self.key)
        except Exception as e:
            st.error(f"Failed to connect to Supabase: {e}")

    def _encode_image(self, image_path):
        """
        Converts a local image file to a Base64 string to store 
        permanently in the cloud database.
        """
        if not image_path or not os.path.exists(image_path):
            return ""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception:
            return ""

    def log_trade(self, ticker, entry, atr_sl, notes, image_path=None):
        """
        Inserts a new trade record into the Supabase 'trades' table.
        """
        encoded_img = self._encode_image(image_path)
        
        data = {
            "ticker": ticker,
            "entry": float(entry),
            "atr_sl": float(atr_sl),
            "notes": notes,
            "image_data": encoded_img
        }
        
        try:
            return self.supabase.table("trades").insert(data).execute()
        except Exception as e:
            st.error(f"Error logging trade: {e}")
            return None

    def get_journal_data(self):
        """
        Fetches all logged trades from Supabase and returns them as a 
        Pandas DataFrame, ordered by the latest timestamp.
        """
        try:
            response = self.supabase.table("trades")\
                .select("*")\
                .order("timestamp", desc=True)\
                .execute()
            
            if response.data:
                return pd.DataFrame(response.data)
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Error fetching journal: {e}")
            return pd.DataFrame()

    def update_notes(self, trade_id, new_notes):
        """
        Updates the notes for a specific trade based on its ID.
        """
        try:
            return self.supabase.table("trades")\
                .update({"notes": new_notes})\
                .eq("id", trade_id)\
                .execute()
        except Exception as e:
            st.error(f"Error updating notes: {e}")

    def delete_trade(self, trade_id):
        """
        Deletes a trade record from the Supabase 'trades' table.
        """
        try:
            return self.supabase.table("trades")\
                .delete()\
                .eq("id", trade_id)\
                .execute()
        except Exception as e:
            st.error(f"Error deleting trade: {e}")

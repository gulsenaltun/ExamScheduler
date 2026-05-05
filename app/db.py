import pyodbc
import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

def get_connection():
    try:
        server = os.getenv("DB_SERVER")
        port = os.getenv("DB_PORT")
        database = os.getenv("DB_NAME")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        
        driver = "{ODBC Driver 18 for SQL Server}"
        
        conn_str = (
            f"DRIVER={driver};"
            f"SERVER={server},{port};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
            "LoginTimeout=30;"
        )
        return pyodbc.connect(conn_str)
    except Exception as e:
        st.error(f"Veritabanı bağlantı hatası (Bağlantı Ayarlarını Kontrol Edin): {e}")
        return None
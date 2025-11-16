import os
import glob
import re
import json
import pandas as pd
import psycopg2
from psycopg2 import sql
from io import StringIO


# =============================================================================
# 💾 CONEXIÓN A BASE DE DATOS
# =============================================================================

def connect_to_postgres():
    """
    Establece una conexión con la base de datos PostgreSQL.

    Usa la variable de entorno `DB_DSN`, que debe contener el string de conexión
    completo en formato psycopg2 (ejemplo: "host=postgres_db dbname=myapp user=admin password=secret").

    Returns:
        psycopg2.connection | None: Objeto de conexión si se logra conectar, o None si falla.
    """
    DB_DSN = os.environ.get("DB_DSN")
    if not DB_DSN:
        print("⚠️ Variable de entorno DB_DSN no definida.")
        return None

    try:
        conn = psycopg2.connect(DB_DSN, connect_timeout=30)
        print("✅ Conectado a PostgreSQL")
        return conn
    except Exception as e:
        print("❌ Error conectando a PostgreSQL:", e)
        return None

# =============================================================================
# 💾 LECTURA DE TABLAS DE SQL CON PANDAS                                                        A DEPRECAR
# =============================================================================

def read_table(query, conn):
    """Lee una tabla o query y devuelve un DataFrame"""
    return pd.read_sql(query, conn)

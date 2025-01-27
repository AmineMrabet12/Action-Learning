import streamlit as st
import psycopg2
from psycopg2 import sql
import os
from dotenv import load_dotenv

load_dotenv()

# Define a function to connect to PostgreSQL
def connect_to_db():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
        )
        return conn
    except Exception as e:
        st.error(f"Error connecting to the database: {e}")
        return None

# Example: Querying the database
def run_query(query):
    conn = connect_to_db()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except Exception as e:
            st.error(f"Error running query: {e}")
            return None

# Streamlit App
st.title("PostgreSQL Connection Example")

query = st.text_area("Enter SQL Query")
if st.button("Run Query"):
    if query:
        results = run_query(query)
        if results:
            st.dataframe(results)
            st.write("Query Results:")
            st.write(results)
    else:
        st.warning("Please enter a query.")

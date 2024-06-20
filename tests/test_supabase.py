import streamlit as st
from supabase import create_client, Client
from st_supabase_connection import SupabaseConnection, execute_query

supabase_url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
supabase_key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]


def initialize_client():
    try:
        st.session_state["client"] = create_client(supabase_url, supabase_key)
        st.session_state["initialized"] = True
        st.success("Client initialized!", icon="✅")
    except Exception as e:
        st.error(f"Client initialization failed: {e}", icon="❌")
        st.session_state["initialized"] = False

def verify_connection() -> bool:
    try:
        # Perform a simple query to verify connection
        query = st.session_state["client"].table("routes").select("*").limit(1)
        st.write("Query created successfully.")
    except Exception as e:
        st.write(f"An error occurred while creating the query: {e}")
        return False

    try:
        response = query.execute()
        st.write("Query executed successfully.")
    except Exception as e:
        st.write(f"An error occurred while executing the query: {e}")
        return False

    try:
        if response and response.data:
            st.write("Connection successful!")
            st.write(response.data)
            return True
        else:
            st.write("Connection failed or no data retrieved.")
            st.write(f"Response data: {response.data if response else 'None'}")
            return False
    except Exception as e:
        st.write(f"An error occurred while handling the response: {e}")
        return False

def list_tables() -> bool:
    try:
        # List all tables in the database
        query = st.session_state["client"].table("information_schema.tables").select("table_name").eq("table_schema", "public")
        response = query.execute()
        if response and response.data:
            st.write("Tables in database:")
            tables = [row['table_name'] for row in response.data]
            for table in tables:
                st.write(table)
            return True
        else:
            st.write("Failed to retrieve tables.")
            st.write(f"Response data: {response.data if response else 'None'}")
            st.write(f"Response error: {response.error if response else 'None'}")
            return False
    except Exception as e:
        st.write(f"An error occurred while listing tables: {e}")
        return False

# Main Function
def main():
    st.title("Supabase Database Interaction")

    # Initialize client if not already initialized
    if "initialized" not in st.session_state or not st.session_state["initialized"]:
        initialize_client()

    # Verify connection and list tables if initialized
    if "initialized" in st.session_state and st.session_state["initialized"]:
        if verify_connection():
            list_tables()

if __name__ == "__main__":
    main()
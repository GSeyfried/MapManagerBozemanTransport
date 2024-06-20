import json
import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_supabase_connection import SupabaseConnection, execute_query
import io
import zipfile

# Define URL and Key Outside of Any Function
supabase_url = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
supabase_key = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
columns_to_select = {
    'stops': ['stop_id', 'stop_name', 'stop_lat', 'stop_lon'],
    'stop_times': ['stop_id', 'trip_id', 'arrival_time', 'stop_sequence', 'shape_dist_traveled'],
    'trips': ['route_id', 'trip_id', 'service_id', 'trip_headsign', 'direction_id', 'shape_id'],
    'routes': ['route_id', 'route_long_name', 'route_color'],
    'calendar_attributes': []
}

# Primary keys for each table
primary_keys = {
    'calendar_attributes': 'service_id',
    'routes': 'route_id',
    'stop_times': 'index',
    'stops': 'stop_id',
    'trips': 'trip_id'
}

# Initialize Client Function


def initialize_client(supabase_url=supabase_url, supabase_key=supabase_key):
    try:
        st.session_state["client"] = create_client(supabase_url, supabase_key)
        st.session_state["initialized"] = True
        st.success(
            "Client initialized! - you are connected to the database", icon="✅")
    except Exception as e:
        st.error(f"Client initialization failed: {e}", icon="❌")
        st.session_state["initialized"] = False

# Pull Selected Files from Supabase


@st.cache_data
def pull_selected_files(tables, columns, comment=True):
    data = {}
    dtypes = {}
    for table in tables:
        col_selection = columns.get(table, '*')
        if isinstance(col_selection, list):
            col_selection = ','.join(col_selection)
        if comment:
            st.write(
                f"Pulling data for: **{table}** with columns: **{col_selection}**")
        query = st.session_state["client"].table(table).select(col_selection)
        response = execute_query(query)
        if response and response.data:
            df = pd.DataFrame(response.data)
            data[table] = df
            dtypes[table] = df.dtypes.to_dict()
            data[table]['source'] = 'database'
    return data, dtypes

# Convert any NA or Null values to None


def clean_data(df):
    df = df.replace({'': None, 'NULL': None})
    df = df.where(pd.notnull(df), None)

    return df

# Upload Table


def upload_table(file, table_name):
    client = st.session_state["client"]
    df = pd.read_csv(file, delimiter=',')
    df = clean_data(df)

    # Ensure all columns match the expected dtypes from the database
    expected_dtypes = st.session_state["dtypes"].get(table_name, {})
    for col, expected_dtype in expected_dtypes.items():
        if col in df.columns:
            df[col] = df[col].astype(expected_dtype)

    try:
        primary_key = primary_keys.get(table_name, None)

        if len(df) > 500:
            df.reset_index(inplace=True)
            primary_key = 'index'

        # columns in the uploaded file match the expected columns
        expected_columns = columns_to_select.get(
            table_name, df.columns.tolist())
        if not set(expected_columns).issubset(df.columns):
            st.error(
                f"Columns in the uploaded file for {table_name} do not match the expected schema.")
            st.write(f"Expected columns: {expected_columns}")
            st.write(f"Uploaded file columns: {df.columns.tolist()}")
            return

        # Delete all rows in the table using an always false condition for a numeric field
        client.table(table_name).delete().neq(primary_key, -1).execute()
        data = df.to_dict(orient='records')

        def clean_row(row):
            for key, value in row.items():
                if pd.isna(value) or value in ('', 'NULL'):
                    row[key] = None
            return row
        data = [clean_row(row) for row in data]

        # Insert new data into the table in chunks
        for i in range(0, len(data), 500):
            chunk = data[i:i+500]
            client.table(table_name).insert(chunk).execute()

        st.success(f"Table {table_name} uploaded successfully.")
    except Exception as e:
        st.error(f"Error occurred while uploading table {table_name}: {e}")


def download_tables():
    required_tables = ['routes', 'calendar_attributes',
                       'stop_times', 'stops', 'trips']
    data = {}

    for table in required_tables:
        query = st.session_state["client"].table(table).select('*')
        response = execute_query(query)
        if response and response.data:
            df = pd.DataFrame(response.data)
            data[table] = df

# download updates log if exists
    try:
        query = st.session_state["client"].table('updates_log').select('*')
        response = execute_query(query)
        if response and response.data:
            df = pd.DataFrame(response.data)
            data[table] = df
    except Exception:
        pass

    if not data:
        st.warning("No tables to download.")
        return

    file_format = st.radio(
        "Choose the file format for download", options=['csv', 'txt'])

    with io.BytesIO() as zip_buffer:
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for table, df in data.items():
                if file_format == 'csv':
                    data_str = df.to_csv(index=False)
                    file_extension = "csv"
                else:
                    data_str = df.to_csv(index=False, sep=',')
                    file_extension = "txt"

                zip_file.writestr(f"{table}.{file_extension}", data_str)

        zip_buffer.seek(0)
        st.download_button(
            label=f"Download all tables as {file_format.upper()} in ZIP",
            data=zip_buffer,
            file_name="supabase_files.zip",
            mime="application/zip"
        )


def process_data():
    # Load data from Supabase
    data, dtypes = pull_selected_files(
        ['stops', 'stop_times', 'trips', 'routes', 'calendar_attributes'], columns_to_select, comment=False)

    # Filter columns
    stop_times = data['stop_times'][['stop_id', 'trip_id',
                                     'arrival_time', 'stop_sequence', 'shape_dist_traveled']]
    stops = data['stops'][['stop_id', 'stop_name', 'stop_lat', 'stop_lon']]
    trips = data['trips'][['route_id', 'trip_id', 'service_id',
                           'trip_headsign', 'direction_id', 'shape_id']]
    routes = data['routes'][['route_id', 'route_long_name', 'route_color']]

    # Merge trips and routes
    routes_by_trip = pd.merge(trips, routes, on='route_id', how='left').drop_duplicates(
        subset=['trip_id'], keep='first')

    # Merge stops and stop times
    stop_time_loc = pd.merge(stop_times, stops, on='stop_id', how='left')

    # Merge stops and routes
    stop_data = pd.merge(stop_time_loc, routes_by_trip,
                         on='trip_id', how='left')

    # Merge calendar attributes with service ID for all stops
    stop_data_service = pd.merge(
        stop_data, data['calendar_attributes'], on='service_id', how='left')

    # Further cleaning of stop data
    stop_data_service['arrival_time'] = pd.to_datetime(
        stop_data_service['arrival_time'], format='%H:%M:%S', errors='coerce')
    stop_data_service['arrival_minutes'] = stop_data_service['arrival_time'].dt.minute + \
        stop_data_service['arrival_time'].dt.hour * 60
    stop_data_service['interpolated_minutes'] = stop_data_service.groupby(
        ['route_id', 'trip_id'])['arrival_minutes'].transform(lambda x: x.interpolate())
    stop_data_service['interpolated_time'] = stop_data_service['interpolated_minutes'].apply(
        lambda x: f"{int(x // 60):02d}:{int(x % 60):02d}:00" if pd.notnull(x) else None)

    # Store processed data in session state
    st.session_state["processed_data"] = {
        'stop_data_service': stop_data_service
    }

    st.success("Data processed and stored successfully.")


def save_updates(updates_df, responce_placeholder):
    supabase = st.session_state.get("client")
    if not supabase:
        responce_placeholder.error(
            "Supabase client is not initialized. Hit that load data button again.")
        return

    # 1: Ensure the 'updates' and 'updates_log' tables exist
    try:
        # responce_placeholder.info("Ensuring 'updates' table exists.")
        response = supabase.rpc("ensure_updates_table_exists").execute()

        # responce_placeholder.info("Ensuring 'updates_log' table exists.")
        response = supabase.rpc("ensure_update_log_table_exists").execute()

    except Exception as e:
        st.error(f"Failed to ensure tables exist: {str(e)}")
        return

    # 2: Insert data into the 'updates' table
    try:
        # responce_placeholder.info("Inserting new data into 'updates' table.")
        updates_json = updates_df.to_json(orient='records')
        updates_data = json.loads(updates_json)
        response = supabase.rpc("insert_updates", {
            'jsonb_array': updates_data
        }).execute()
        responce_placeholder.success("Updated all stop IDs successfully.")
    except Exception as e:
        responce_placeholder.error(
            f"Failed to update 'updates' table: {str(e)}")
        # responce_placeholder.write(f"Exception details: {str(e)}")
        return

    # 3: Log the update action
    try:
        # responce_placeholder.info("Logging updates to 'updates_log' table.")
        response = supabase.rpc("insert_update_logs").execute()
        # responce_placeholder.success("Logged all updates successfully.")
    except Exception as e:
        responce_placeholder.error(f"Failed to log updates: {str(e)}")
        # responce_placeholder.write(f"Exception details: {str(e)}")
        return

    # Step 4: Update routes based on the 'updates' table
    try:
        # responce_placeholder.info("Updating routes based on 'updates' table.")
        response = supabase.rpc("update_routes_from_updates").execute()
       # responce_placeholder.success("Routes updated successfully.")
    except Exception as e:
        responce_placeholder.error(f"Failed to update routes: {str(e)}")
       # responce_placeholder.write(f"Exception details: {str(e)}")

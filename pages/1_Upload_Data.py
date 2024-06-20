import streamlit as st
import pandas as pd
from components.databasefuncs import initialize_client, pull_selected_files, upload_table, download_tables, process_data, columns_to_select
from components.menu import menu_with_redirect

# Initialize user session and verify login
menu_with_redirect()

# Verify the user's role
if not st.session_state.get("authentication_status", False):
    st.warning("You do not have permission to view this page.")
    st.stop()
                
st.title("Load Maps Data")
st.markdown('''This page allows you to upload google maps files to adjust in the map viewer page. 
            All of the files are stored on a lightweight database, so you can proceed without uploading anything. 
            If you believe that you have an updated copy of one of the following files, then hit that replace table button 
            to permanently replace the particular file.''')
st.markdown('''**Currently this app operates on files:**
            routes.txt, stops.txt, stop_times,txt, trips.txt, calendar_attributes.txt''')

# Initialize client
if "initialized" not in st.session_state or not st.session_state["initialized"]:
    initialize_client()

required_files = ["routes", "stops", "stop_times", "trips", "calendar_attributes"]

uploaded_files = st.file_uploader("Upload your files", accept_multiple_files=True, type=["txt", "csv"])

# Initialize data_loaded ss
if "data_loaded" not in st.session_state:
    st.session_state['data_loaded'] = False

# Initialize dtypes ss
if "dtypes" not in st.session_state:
    st.session_state['dtypes'] = {}

#initialize processed_data ss
if 'processed_data' not in st.session_state:
    st.session_state["processed_data"] = {}

if st.button("Load Data from Database"):
    st.session_state['data_loaded'] = True
    data, dtypes = pull_selected_files(required_files, columns_to_select)
    st.session_state["dtypes"] = dtypes 

    if uploaded_files:
        # Process uploaded files and replace corresponding data
        for file in uploaded_files:
            table_name = file.name.split('.')[0]
            df = pd.read_csv(file)
            df['source'] = 'uploaded'
            data[table_name] = df
    
    process_data()

if st.session_state['data_loaded']:
    st.subheader("Replace Table Data in Database with Upload")
    st.markdown("Click this button if you want the permanently stored files to be replaced by the copy you have uploaded.")
    if uploaded_files:
        replace_selections = {file.name: st.checkbox(file.name, value=True) for file in uploaded_files}

        if st.button("Replace Tables"):
            for file in uploaded_files:
                if replace_selections[file.name]:
                    table_name = file.name.split('.')[0]
                    upload_table(file, table_name)
    else:
        st.warning("No files uploaded to replace. Upload files to view button.")
    
    # Add download CSV button
    download_tables()


col1, col2 = st.columns([5,1])

with col2:
        if st.session_state.data_loaded is True:
            if st.button("Continue"):
                st.switch_page("pages/2_Adjust_Map.py")

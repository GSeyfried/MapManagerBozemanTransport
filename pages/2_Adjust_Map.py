import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from datetime import datetime
from components.menu import menu_with_redirect
from components.map import *
from components.databasefuncs import process_data, save_updates

### Set up page ensure logged in ###

# Initialize user session and verify login
menu_with_redirect()

# Verify the user's role
if not st.session_state.get("authentication_status", False):
    st.warning("You do not have permission to view this page.")
    st.stop()

# inizitalize delete input for buttons at the bottom
if 'clear_delete_input' in st.session_state and st.session_state['clear_delete_input']:
    st.session_state['delete_input'] = ''
    st.session_state['clear_delete_input'] = False

bozeman_coords = [45.6770, -111.0429]

# initialize location session state with fill in coords
if "latitude" not in st.session_state:
    st.session_state["latitude"] = bozeman_coords[0]
if "longitude" not in st.session_state:
    st.session_state["longitude"] = bozeman_coords[1]


def updated_location():
    return [st.session_state["latitude"], st.session_state["longitude"]]


# Title
st.title("Live Location Map Updates")

if st.button("Upload Data (previous page)"):
    st.switch_page("pages/1_Upload_Data.py")

    ### Build map and put Bus stops on viewer ###

# Initialize a folium map
m = folium.Map(location=bozeman_coords, zoom_start=14, tiles='cartodbpositron')


# pull processed data from session state or cached data return error if neither
try:
    try:
        stop_data_service = st.session_state["processed_data"]["stop_data_service"]
    except:
        if "processed_data" not in st.session_state or "stop_data_service" not in st.session_state["processed_data"]:
            # Call process_data to load cached data
            process_data()
            stop_data_service = st.session_state["processed_data"]["stop_data_service"]
except:
    st.warning("Sorry It looks like the data got erased, this sometimes happens when a page reloads improperly. Make sure you save updates frequently, because you will have to reload the webpage and log in again.")
bus_lines = organize_by_bus_line(
    stop_data_service)  # organize data by bus line
selected_bus_line = st.selectbox("Select Bus Line", options=bus_lines.keys())

# Add bus stops to the map
if selected_bus_line in bus_lines:
    bus_stops = bus_lines[selected_bus_line]
    unique_stops = bus_stops[['stop_lat', 'stop_lon', 'stop_id',
                              'stop_name', 'interpolated_time']].drop_duplicates()
    for _, stop in unique_stops.iterrows():
        marker = folium.Marker(location=[stop['stop_lat'], stop['stop_lon']],
                               popup=f"{stop['stop_name']} <br>ID:{stop['stop_id']} <br> Time:{stop.get('interpolated_time', 'unknown')}")
        marker.add_to(m)

        ### Live Location ###

loc = get_geolocation(component_key='init')

# Update session state with the live location & Put on map
if loc:
    st.session_state["latitude"] = loc['coords']['latitude']
    st.session_state["longitude"] = loc['coords']['longitude']

live_location = updated_location()
folium.Marker(location=live_location, popup="You are here!",
              icon=folium.Icon(color="red")).add_to(m)

# Write Coords
st.write(
    f"Live Latitude: {st.session_state['latitude']}, Live Longitude: {st.session_state['longitude']}")

# Display map
st_data = st_folium(m, width=700, height=500)

# Input stop id manually for developement
stop_ids = bus_stops['stop_id']
entered_stop_id = st.text_input("Enter a stop ID")
replace_map_stop_input = {',': '', ' ': '', 'ID:': '', ':': '', 'D:': ''}
for key, value in replace_map_stop_input.items():
    entered_stop_id = entered_stop_id.replace(key, value)
try:
    entered_stop_id = int(entered_stop_id)
except ValueError:
    st.error("The entered stop ID is not a valid integer.")
stop_ids = stop_ids.astype(int)
if entered_stop_id:
    if entered_stop_id in stop_ids.values:
        st.write(
            f"Accessing: {bus_stops.loc[bus_stops['stop_id'] == entered_stop_id, 'stop_name'].values[0]} stop")
    else:
        st.write(
            "The entered stop ID does not match any stops in the selected bus line.")

if "updates_df" not in st.session_state:
    st.session_state.updates_df = pd.DataFrame(
        columns=['table', 'bus_line', 'stop_id', 'init_lat', 'new_lat', 'init_lon', 'new_lon', 'user', 'time'])

# log updates to updates_df
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    # refresh location
    if st.button("Refresh Location"):
        unique_key = datetime.now().strftime("%Y%m%d%H%M%S%f")
        loc = get_geolocation(component_key=unique_key)
        if loc:
            st.session_state["latitude"] = loc['coords']['latitude']
            st.session_state["longitude"] = loc['coords']['longitude']
        st.rerun()

with col2:
    # move stop to user location
    if st.button("Move stop to user location"):
        formatted_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        update_row = {
            'table': 'stops',
            'bus_line': selected_bus_line,
            'stop_id': [entered_stop_id],
            'init_lat': [bus_stops.loc[bus_stops['stop_id'] == entered_stop_id, 'stop_lat'].values[0]],
            'new_lat': [st.session_state['latitude']],
            'init_lon': [bus_stops.loc[bus_stops['stop_id'] == entered_stop_id, 'stop_lon'].values[0]],
            'new_lon': [st.session_state['longitude']],
            'user': [st.session_state["name"]],
            'time': [formatted_time]
        }
        update_row_df = pd.DataFrame(update_row)
        st.session_state['updates_df'] = pd.concat(
            [st.session_state['updates_df'], update_row_df], ignore_index=True)
if entered_stop_id:
    # write update and show df
    st.warning(f"""Stop {bus_stops.loc[bus_stops['stop_id'] == entered_stop_id, 'stop_name'].values[0]} has been moved
                    from {bus_stops.loc[bus_stops['stop_id'] == entered_stop_id, 'stop_lat'].values[0]},{bus_stops.loc[bus_stops['stop_id'] == entered_stop_id, 'stop_lon'].values[0]} 
                    to {st.session_state['latitude']},{st.session_state['longitude']}""")

st.divider()

# Use Streamlit columns to layout the buttons and input field next to each other
col1, col2, col3 = st.columns([1, 2, 1])
responce_placeholder = st.empty()

# Delete Last Update
with col1:
    if st.button("Delete Last Update"):
        if not st.session_state['updates_df'].empty:
            # Remove the last row
            st.session_state['updates_df'] = st.session_state.updates_df[:-1]
            st.success("Last update deleted.")
        else:
            st.error("No data to delete.")

# delete update by row number or stop id
with col2:
    delete_input = st.text_input("stop ID input",
                                 on_change=None,
                                 key="delete_input",
                                 placeholder="Row number that you want to remove.",
                                 label_visibility='collapsed')
    if st.button("Delete Row", key="delete_row_button"):
        if delete_input:
            row_number = int(delete_input)
            if 0 <= row_number < len(st.session_state.updates_df):
                st.session_state['updates_df'] = st.session_state['updates_df'].drop(
                    st.session_state['updates_df'].index[row_number]).reset_index(drop=True)
                st.success(f"Row {row_number} deleted.")
                # flag delete input for next run
                st.session_state['clear_delete_input'] = True
            else:
                st.error("Row number out of range.")
            # Clear the input after processing

st.write(st.session_state.updates_df)

# Save Data functionality in the third column
with col3:
    if st.button("Save Data"):
        if st.session_state['updates_df'] is not None:
            for _, row in st.session_state['updates_df'].iterrows():
                stop_id = row['stop_id']
                new_lat = row['new_lat']
                new_lon = row['new_lon']
                stop_data_service.loc[stop_data_service['stop_id']
                                      == stop_id, 'stop_lat'] = new_lat
                stop_data_service.loc[stop_data_service['stop_id']
                                      == stop_id, 'stop_lon'] = new_lon
                user = row['user']
                bus_line = row['bus_line']
            try:
                save_updates(st.session_state.updates_df, responce_placeholder)
                responce_placeholder.success("Saved successfully!")
            except:
                responce_placeholder.error("Failed to save.")
        # else:
            # st.error("Required data not found in session state.")

        try:
            st.rerun()
        except:
            responce_placeholder.error("Refresh Page to update map view.")

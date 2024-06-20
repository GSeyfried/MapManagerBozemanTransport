import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import Draw
import pandas as pd

@st.cache_data
def load_pickle(filepath):
    try:
        loaded_data = pd.read_pickle(filepath)
        print("Data loaded successfully:", loaded_data.keys())
        return loaded_data
    except Exception as e:
        print("Error loading the pickle file:", str(e))
        return None
    
def create_route_map(trip_data, geojson_data, line_name):
    if trip_data.empty:
        raise ValueError("Trip data is empty. Cannot create map.")
    start_lat = trip_data['stop_lat'].iloc[0]
    start_lon = trip_data['stop_lon'].iloc[0]

    m = folium.Map(location=[start_lat, start_lon], zoom_start=13, tiles='cartodbpositron')
    for _, row in trip_data.iterrows():
        marker = folium.Marker(
            [row['stop_lat'], row['stop_lon']],
            popup=f"{row['stop_name']}<br>Time: {row.get('interpolated_time', 'Unknown')}"
        )
        marker.add_to(m)

    folium.GeoJson(
        geojson_data[line_name],
        name=line_name,
        style_function=lambda x: {'color': 'blue', 'weight': 2.5, 'opacity': 1}
    ).add_to(m)

    draw = Draw(
        draw_options={
            'polyline': {'allowIntersection': True},
            'polygon': {'allowIntersection': False},
            'rectangle': False,
            'circle': False,
            'marker': True,
            'circlemarker': False
        },
        edit_options={'edit': False}
    )
    draw.add_to(m)

    return m

def main():
    st.set_page_config(layout="wide")
    st.title('Bus and Walking Route Editor')

    stops = load_pickle('route_dictionaries.pkl')
    routes = load_pickle('transformed_routes_geojson.pkl')

    bus_line = st.selectbox('Select a bus line:', ['Choose a line', 'Blueline', 'Goldline'])
    if bus_line != 'Choose a line':
        # Filter trips based on frequency and day
        day_filter = st.radio("Select Day Type:", ('Weekday', 'Weekend'))
        hide_half_hour = st.checkbox("Show Half-Hour Frequency (Fall through Spring Only)", False)

        trips = [trip for trip in stops[bus_line].keys() if
                 (day_filter in trip) and
                 (hide_half_hour or '1/2Hour' not in trip)]

        selected_trip = st.selectbox('Select a trip:', ['Choose a trip'] + trips)
        col1, col2 = st.columns(2)
        with col1:
            if selected_trip and selected_trip != 'Choose a trip':
                with st.spinner('Loading map...'):
                    trip_map = create_route_map(stops[bus_line][selected_trip], routes, bus_line)
                    st_folium(trip_map, height=600)

        with col2:
            if selected_trip and selected_trip != 'Choose a trip':
                st.dataframe(stops[bus_line][selected_trip])

if __name__ == "__main__":
    main()
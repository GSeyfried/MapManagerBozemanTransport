import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit.components.v1 import html


@st.cache_data
def organize_by_bus_line(df):
    bus_lines = {}
    for line in df['route_long_name'].unique():
        if line not in bus_lines:
            bus_lines[line] = []
        bus_lines[line].append(df[df['route_long_name'] == line])
    return {line: pd.concat(dfs) for line, dfs in bus_lines.items()}



def location_update():
    latitude = st.session_state.get("latitude", 0)
    longitude = st.session_state.get("longitude", 0)
    return latitude, longitude


# Add JavaScript to listen for the custom event and update session state
html("""
<script>
document.addEventListener('locationUpdate', function(event) {
    const coordinates = event.detail;
    fetch('/_stcore_/update_session', {
        method: 'POST',
        body: JSON.stringify(coordinates),
        headers: new Headers({'Content-Type': 'application/json'})
    }).then(response => response.json()).then(data => {
        window.location.reload();
    });
});
</script>
""")

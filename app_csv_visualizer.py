import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import math

# Set page layout
st.set_page_config(layout="wide", page_title="Telecom Sector Visualizer")

st.title("Telecom Sector Visualizer 📡")
st.markdown("Visualize telecom sectors on a map based on CSV data.")

# --- Sidebar Configuration ---
st.sidebar.header("Map Settings")
sector_radius = st.sidebar.slider("Sector Radius (meters)", min_value=50, max_value=2000, value=300, step=50)
fill_opacity = st.sidebar.slider("Fill Opacity", min_value=0.0, max_value=1.0, value=0.5, step=0.1)
sector_color = st.sidebar.color_picker("Sector Color", "#3388ff")

# --- Helper Functions ---

def get_sector_polygon(lat, lon, azimuth, beamwidth, radius_meters):
    """
    Generates a polygon representing a sector (wedge).
    
    Args:
        lat (float): Latitude of the center.
        lon (float): Longitude of the center.
        azimuth (float): Azimuth in degrees (0 is North, clockwise).
        beamwidth (float): Horizontal beamwidth in degrees.
        radius_meters (float): Radius of the sector in meters.
        
    Returns:
        list: A list of (lat, lon) tuples forming the polygon.
    """
    R = 6378137.0  # Earth's radius in meters
    
    # Half beamwidth to determine start and end angles relative to azimuth
    half_bw = beamwidth / 2.0
    start_angle = azimuth - half_bw
    end_angle = azimuth + half_bw
    
    # Generate points along the arc
    # We'll use 1 point per degree for smoothness, or fewer for performance if needed
    num_points = int(beamwidth) if beamwidth > 10 else 10
    if num_points < 3: num_points = 3
    
    angles = [start_angle + (end_angle - start_angle) * i / (num_points - 1) for i in range(num_points)]
    
    polygon_points = [(lat, lon)] # Start at center
    
    for angle in angles:
        # Convert angle to radians. 
        # Note: Math functions usually expect angle from X-axis (East) counter-clockwise.
        # But geographic Azimuth is from North (Y-axis) clockwise.
        # Standard math conversion: bearing (deg) -> math_angle (rad)
        # math_angle = (90 - bearing) * pi / 180
        
        # However, for destination point formula we can use bearing directly if we implement standard geodetic formula.
        # Destination point given distance and bearing from start point:
        # φ2 = asin( sin φ1 ⋅ cos δ + cos φ1 ⋅ sin δ ⋅ cos θ )
        # λ2 = λ1 + atan2( sin θ ⋅ sin δ ⋅ cos φ1, cos δ − sin φ1 ⋅ sin φ2 )
        # where φ is lat, λ is lon, θ is bearing (clockwise from north), δ is angular distance d/R
        
        theta = math.radians(angle)
        delta = radius_meters / R
        phi1 = math.radians(lat)
        lam1 = math.radians(lon)
        
        phi2 = math.asin(math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta))
        lam2 = lam1 + math.atan2(math.sin(theta) * math.sin(delta) * math.cos(phi1), math.cos(delta) - math.sin(phi1) * math.sin(phi2))
        
        p_lat = math.degrees(phi2)
        p_lon = math.degrees(lam2)
        
        polygon_points.append((p_lat, p_lon))
        
    polygon_points.append((lat, lon)) # Close the loop back to center
    
    return polygon_points

# --- Main App Logic ---

uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

REQUIRED_COLUMNS = ['ENODEB_ID', 'CELL_ID', 'LONGITUDE', 'LATITUDE', 'AZIMUTH', 'BEAMWIDTH_H']

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        
        # Check columns
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            st.error(f"Missing required columns in CSV: {', '.join(missing_cols)}")
        else:
            # Data Cleaning
            df = df.dropna(subset=REQUIRED_COLUMNS)
            st.success(f"Loaded {len(df)} sectors successfully.")
            
            with st.expander("View Raw Data"):
                st.dataframe(df.head())

            if len(df) > 0:
                # Calculate simple center for initial map view
                center_lat = df['LATITUDE'].mean()
                center_lon = df['LONGITUDE'].mean()
                
                m = folium.Map(location=[center_lat, center_lon], zoom_start=14)
                
                # Add sectors
                for i, row in df.iterrows():
                    try:
                        lat = float(row['LATITUDE'])
                        lon = float(row['LONGITUDE'])
                        azimuth = float(row['AZIMUTH'])
                        bw = float(row['BEAMWIDTH_H'])
                        
                        points = get_sector_polygon(lat, lon, azimuth, bw, sector_radius)
                        
                        tooltip_text = f"<b>ENodeB:</b> {row['ENODEB_ID']}<br><b>Cell ID:</b> {row['CELL_ID']}<br><b>Azimuth:</b> {azimuth}<br><b>Beamwidth:</b> {bw}"
                        
                        folium.Polygon(
                            locations=points,
                            color='black', # Border color
                            weight=1,
                            fill=True,
                            fill_color=sector_color,
                            fill_opacity=fill_opacity,
                            tooltip=tooltip_text
                        ).add_to(m)
                        
                    except Exception as e:
                        st.warning(f"Error plotting row {i}: {e}")
                        continue

                    if i > 100:
                        break

                st_folium(m, width="100%", height=600)
                
            else:
                st.warning("Dataframe empty after removing rows with missing values.")
                
    except Exception as e:
        st.error(f"Error reading file: {e}")

else:
    st.info("Please upload a CSV file with the following columns: " + ", ".join(REQUIRED_COLUMNS))
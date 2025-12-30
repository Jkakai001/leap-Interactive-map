#!/usr/bin/env python3
"""
Interactive Pittsburgh Map with Boundaries and Landmarks
Author: John M. Kakai
Description: Creates an interactive map of Pittsburgh with city boundaries,
             known landmarks, and clickable locations with detailed information.
"""

import folium
import json
import requests
from typing import Dict, List, Tuple, Optional
import pandas as pd
from folium import plugins
import webbrowser
import os
import hashlib
import base64
import http.server
import socketserver
import threading
import time
from urllib.parse import quote

# Try to import geopandas for shapefile support
try:
    import geopandas as gpd
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False
    try:
        import fiona
        HAS_FIONA = True
    except ImportError:
        HAS_FIONA = False

# Try to import gspread for Google Sheets support
try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

class PittsburghMap:
    def __init__(self):
        """Initialize the Pittsburgh map with center coordinates."""
        # Pittsburgh city center coordinates
        self.center_lat = 40.4406
        self.center_lon = -79.9959
        self.map = None
        self.image_cache_dir = os.path.join('files', 'images')
        try:
            os.makedirs(self.image_cache_dir, exist_ok=True)
        except Exception:
            pass
        
        # Store LEAP locations for later use
        self.leap_locations = []
        
        # Known Pittsburgh landmarks and their data
        self.landmarks = [
            {
                'name': 'Point State Park',
                'lat': 40.4417,
                'lon': -79.9967,
                'description': 'Historic park at the confluence of three rivers',
                'website': 'https://www.dcnr.pa.gov/StateParks/FindAPark/PointStatePark/Pages/default.aspx',
                'tags': ['park', 'history', 'rivers', 'monument'],
                'photo_alt': 'https://stock.adobe.com/search?k=pittsburgh+point+state+park',
                #'photo_url': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Point_State_Park_Fountain.jpg/800px-Point_State_Park_Fountain.jpg'
            },
            {
                'name': 'Carnegie Mellon University',
                'lat': 40.4426,
                'lon': -79.9445,
                'description': 'Premier research university known for computer science and robotics',
                'website': 'https://www.cmu.edu/',
                'tags': ['university', 'education', 'research', 'technology'],
                'photo_url': 'https://images.unsplash.com/photo-1562774053-701939374585?w=800&h=600&fit=crop'
            },
            {
                'name': 'University of Pittsburgh',
                'lat': 40.4448,
                'lon': -79.9535,
                'description': 'Major public research university with iconic Cathedral of Learning',
                'website': 'https://www.pitt.edu/',
                'tags': ['university', 'education', 'research', 'architecture'],
                'photo_url': 'https://images.unsplash.com/photo-1541339907198-e08756dedf3f?w=800&h=600&fit=crop'
            },
            {
                'name': 'PNC Park',
                'lat': 40.4469,
                'lon': -80.0057,
                'description': 'Home of the Pittsburgh Pirates baseball team',
                'website': 'https://www.mlb.com/pirates/ballpark',
                'tags': ['sports', 'baseball', 'stadium', 'entertainment'],
                'photo_url': 'https://images.unsplash.com/photo-1566577739112-5180d4bf9390?w=800&h=600&fit=crop'
            },
            {
                'name': 'Heinz Field',
                'lat': 40.4468,
                'lon': -80.0158,
                'description': 'Home of the Pittsburgh Steelers and Pitt Panthers football teams',
                'website': 'https://www.heinzfield.com/',
                'tags': ['sports', 'football', 'stadium', 'entertainment'],
                'photo_url': 'https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=800&h=600&fit=crop'
            },
            {
                'name': 'Andy Warhol Museum',
                'lat': 40.4484,
                'lon': -80.0025,
                'description': 'Largest museum dedicated to a single artist in North America',
                'website': 'https://www.warhol.org/',
                'tags': ['museum', 'art', 'culture', 'history'],
                'photo_url': 'https://images.unsplash.com/photo-1541961017774-22349e4a1262?w=800&h=600&fit=crop'
            },
            {
                'name': 'Duquesne Incline',
                'lat': 40.4396,
                'lon': -80.0169,
                'description': 'Historic cable car offering panoramic city views',
                'website': 'https://www.duquesneincline.org/',
                'tags': ['transportation', 'history', 'views', 'tourist'],
                'photo_url': 'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop'
            }
        ]

    def create_base_map(self) -> folium.Map:
        """Create the base interactive map centered on Pittsburgh."""
        # Create map with OSM as the default base layer
        self.map = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=12,
            tiles='OpenStreetMap'  # Standard OSM tiles (light theme)
        )
        
        # Add additional tile layers (OSM is already the default/active layer)
        folium.TileLayer('CartoDB positron', name='CartoDB Positron (Light)').add_to(self.map)
        folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark Matter (Dark)').add_to(self.map)
        
        # Initialize overlay groups for better control
        self.landmarks_group = folium.FeatureGroup(name='Landmarks', show=True)
        self.custom_group = folium.FeatureGroup(name='Custom Locations', show=True)
        self.leap_group = folium.FeatureGroup(name='LEAP Locations', show=True)
        self.landmarks_group.add_to(self.map)
        self.custom_group.add_to(self.map)
        self.leap_group.add_to(self.map)
        
        return self.map

    def add_pittsburgh_boundary(self):
        """Add Pittsburgh city boundary using approximate coordinates."""
        # Simplified Pittsburgh city boundary coordinates
        pittsburgh_boundary = [
            [40.5200, -80.1000],  # Northwest
            [40.5200, -79.8500],  # Northeast  
            [40.3500, -79.8500],  # Southeast
            [40.3500, -80.1000],  # Southwest
            [40.5200, -80.1000]   # Close the polygon
        ]
        
        folium.Polygon(
            locations=pittsburgh_boundary,
            color='blue',
            weight=3,
            fillColor='lightblue',
            fillOpacity=0.1,
            popup='Pittsburgh City Boundary'
        ).add_to(self.map)

    def fetch_boundary_from_osm(self, relation_id: int = 162208):
        """Fetch Pittsburgh boundary from OSM using Overpass API.
        
        Args:
            relation_id: OSM relation ID for Pittsburgh (default: 162208)
        """
        try:
            overpass_url = "https://overpass-api.de/api/interpreter"
            query = f"""
            [out:json][timeout:25];
            (
              relation({relation_id});
            );
            out geom;
            """
            response = requests.get(overpass_url, params={'data': query}, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('elements'):
                # Convert OSM relation to GeoJSON
                element = data['elements'][0]
                if 'members' in element:
                    # Build polygon from relation members
                    coords = []
                    for member in element.get('members', []):
                        if member.get('type') == 'way' and 'geometry' in member:
                            way_coords = [[point['lat'], point['lon']] for point in member['geometry']]
                            coords.extend(way_coords)
                    
                    if coords:
                        # Close the polygon
                        if coords[0] != coords[-1]:
                            coords.append(coords[0])
                        
                        folium.Polygon(
                            locations=coords,
                            color='#2c7fb8',
                            weight=2,
                            fillColor='#7fcdbb',
                            fillOpacity=0.08,
                            popup='Pittsburgh City Boundary (from OSM)'
                        ).add_to(self.map)
                        return True
            return False
        except Exception as e:
            return False

    def add_boundary_from_shapefile(self, shapefile_path: str, name: str = 'Pittsburgh Boundary'):
        """Add boundary from a shapefile to the Folium map.
        
        Args:
            shapefile_path: Path to the .shp file (or directory containing it)
            name: Display name for the boundary layer
        """
        try:
            if HAS_GEOPANDAS:
                # Use geopandas (easiest method)
                gdf = gpd.read_file(shapefile_path)
                # Convert to GeoJSON, handling non-serializable types
                boundary_geojson = json.loads(gdf.to_json(date_format='iso'))
            elif HAS_FIONA:
                # Use fiona as fallback
                import fiona
                from datetime import datetime
                import pandas as pd
                features = []
                with fiona.open(shapefile_path) as src:
                    for feature in src:
                        # Clean properties to remove non-serializable types
                        props = {}
                        for k, v in feature['properties'].items():
                            try:
                                if isinstance(v, datetime):
                                    props[k] = v.isoformat()
                                elif hasattr(pd, 'Timestamp') and isinstance(v, pd.Timestamp):
                                    props[k] = v.isoformat()
                                elif hasattr(pd, 'isna') and pd.isna(v):
                                    props[k] = None
                                else:
                                    props[k] = v
                            except Exception:
                                # Fallback: convert to string if serialization fails
                                props[k] = str(v) if v is not None else None
                        features.append({
                            'type': 'Feature',
                            'geometry': feature['geometry'],
                            'properties': props
                        })
                boundary_geojson = {'type': 'FeatureCollection', 'features': features}
            else:
                return False
            
            folium.GeoJson(
                boundary_geojson,
                name=name,
                style_function=lambda feature: {
                    'color': '#2c7fb8',
                    'weight': 2,
                    'fillColor': '#7fcdbb',
                    'fillOpacity': 0.08
                }
            ).add_to(self.map)
            return True
        except Exception as e:
            return False

    def add_boundary_geojson(self, geojson_path: str, name: str = 'Pittsburgh Boundary'):
        """Add a real boundary from a local GeoJSON file to the Folium map."""
        try:
            with open(geojson_path, 'r') as f:
                boundary_geojson = json.load(f)
            folium.GeoJson(
                boundary_geojson,
                name=name,
                style_function=lambda feature: {
                    'color': '#2c7fb8',
                    'weight': 2,
                    'fillColor': '#7fcdbb',
                    'fillOpacity': 0.08
                }
            ).add_to(self.map)
            return True
        except Exception as e:
            return False

    def add_landmarks(self):
        """Add known Pittsburgh landmarks with detailed information."""
        for landmark in self.landmarks:
            photo_src = self._get_image_src(landmark.get('photo_url')) if landmark.get('photo_url') else None
            # Create popup content with HTML
            popup_html = f"""
            <div style="width: 300px;">
                <h3 style="color: #2c3e50; margin-bottom: 10px;">{landmark['name']}</h3>
                <p style="margin-bottom: 10px; font-size: 14px;">{landmark['description']}</p>
                
                <div style="margin-bottom: 10px;">
                    <strong>Tags:</strong> {', '.join(landmark['tags'])}
                </div>
                
                {f'<div style="margin-bottom: 10px;"><img src="{photo_src}" style="width: 100%; height: 150px; object-fit: cover; border-radius: 5px;" alt="{landmark["name"]}" loading="lazy" decoding="async" onerror="this.onerror=null;this.src=&quot;https://via.placeholder.com/400x300/cccccc/000000?text=Image+Unavailable&quot;;"></div>' if photo_src else ''}
                
                <div style="text-align: center;">
                    <a href="{landmark['website']}" target="_blank" 
                       style="background-color: #3498db; color: white; padding: 8px 16px; 
                              text-decoration: none; border-radius: 5px; display: inline-block;">
                        Visit Website
                    </a>
                </div>
            </div>
            """
            
            # Add marker with custom icon
            folium.Marker(
                location=[landmark['lat'], landmark['lon']],
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=landmark['name'],
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(self.landmarks_group)

    def load_leap_locations_from_csv(self, csv_path: str = 'files/locations/leap_locations.csv') -> List[Dict]:
        """Load LEAP locations from a CSV file.
        
        Args:
            csv_path: Path to the CSV file containing LEAP locations
            
        Returns:
            List of location dictionaries with name, lat, lon, description, address
        """
        locations = []
        try:
            if not os.path.exists(csv_path):
                return locations
            
            # Read CSV with proper handling of quoted fields and multi-line descriptions
            # Try different encodings if UTF-8 fails
            try:
                df = pd.read_csv(csv_path, quotechar='"', skipinitialspace=True, on_bad_lines='skip', encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(csv_path, quotechar='"', skipinitialspace=True, on_bad_lines='skip', encoding='latin-1')
                except:
                    df = pd.read_csv(csv_path, quotechar='"', skipinitialspace=True, on_bad_lines='skip', encoding='cp1252')
            
            # Drop any completely empty rows
            df = df.dropna(how='all')
            
            for idx, row in df.iterrows():
                try:
                    # Get organization name - use bracket notation for DataFrame access
                    org_name = str(row['ORGANIZATION NAME']).strip() if 'ORGANIZATION NAME' in row else ''
                    if not org_name or org_name == 'nan' or org_name == '':
                        continue
                    
                    # Parse coordinates (format: "lat, lon")
                    coords_str = str(row['XY-COODRINATE']).strip() if 'XY-COODRINATE' in row else ''
                    if not coords_str or coords_str == 'nan' or coords_str == '':
                        continue
                    
                    # Remove quotes if present
                    coords_str = coords_str.strip('"').strip("'").strip()
                    
                    # Split by comma and convert to float
                    try:
                        lat_str, lon_str = coords_str.split(',')
                        lat = float(lat_str.strip())
                        lon = float(lon_str.strip())
                        
                        # Validate coordinates are reasonable (Pittsburgh area)
                        if not (40.0 <= lat <= 41.0) or not (-81.0 <= lon <= -79.0):
                            continue
                            
                    except (ValueError, AttributeError):
                        continue
                    
                    # Get address and description
                    address = str(row['ADDRESS']).strip() if 'ADDRESS' in row else ''
                    description = str(row['BRIEF DESCRIPTION']).strip() if 'BRIEF DESCRIPTION' in row else ''
                    
                    # Clean up address and description (remove 'nan' strings)
                    if address == 'nan':
                        address = ''
                    if description == 'nan':
                        description = 'No description available'
                    
                    # Get website and photo_url from CSV if columns exist, otherwise use mapping
                    website = str(row.get('WEBSITE', '')).strip() if 'WEBSITE' in row else ''
                    photo_url = str(row.get('PHOTO_URL', '')).strip() if 'PHOTO_URL' in row else ''
                    
                    # Clean up website and photo_url
                    if website == 'nan' or website == '':
                        website = ''
                    if photo_url == 'nan' or photo_url == '':
                        photo_url = ''
                    
                    # Mapping of organization names to websites and photos (can be extended)
                    org_websites = {
                        'Phipps Conservatory and Botanical Gardens': 'https://www.phipps.conservatory.org/',
                        'The National Opera House': 'https://www.nationaloperahouse.org/',
                        'Artists Image Resource': 'https://www.airpgh.org/',
                        'BootUP PGH': 'https://www.bootuppgh.org/',
                        'Creative Citizen Studios': 'https://www.creativecitizenstudios.org/',
                        'ARYSE (Alliance for Refugee Youth Support and Education)': 'https://www.arysepgh.org/',
                        'Saturday Light Brigade': 'https://www.slbradio.org/',
                        'Pittsburgh Center For Creative Reuse': 'https://www.pccr.org/',
                        '412 Food Rescue': 'https://www.412foodrescue.org/',
                        "Pittsburgh's Public Source": 'https://www.publicsource.org/',
                        'Casa San José': 'https://www.casasanjose.org/',
                        'Duolingo': 'https://www.duolingo.com/',
                        'YogaRoots On Location': 'https://www.yogarootsonlocation.com/',
                        'Justseeds Artists\' Cooperative': 'https://www.justseeds.org/',
                    }
                    
                    # Mapping of organization names to photo URLs (can be extended with actual images)
                    org_photos = {
                        'Phipps Conservatory and Botanical Gardens': 'https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=800&h=600&fit=crop',
                        'The National Opera House': 'https://images.unsplash.com/photo-1503095396549-807759245b35?w=800&h=600&fit=crop',
                        'Artists Image Resource': 'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=800&h=600&fit=crop',
                        'BootUP PGH': 'https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=800&h=600&fit=crop',
                        'Creative Citizen Studios': 'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=800&h=600&fit=crop',
                        'ARYSE (Alliance for Refugee Youth Support and Education)': 'https://images.unsplash.com/photo-1503676260721-1d00da88a82c?w=800&h=600&fit=crop',
                        'Saturday Light Brigade': 'https://images.unsplash.com/photo-1478737270239-2f02b77fc618?w=800&h=600&fit=crop',
                        'Pittsburgh Center For Creative Reuse': 'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=800&h=600&fit=crop',
                        '412 Food Rescue': 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=800&h=600&fit=crop',
                        "Pittsburgh's Public Source": 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&h=600&fit=crop',
                        'Casa San José': 'https://images.unsplash.com/photo-1503676260721-1d00da88a82c?w=800&h=600&fit=crop',
                        'Duolingo': 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=800&h=600&fit=crop',
                        'YogaRoots On Location': 'https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=800&h=600&fit=crop',
                        'Justseeds Artists\' Cooperative': 'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=800&h=600&fit=crop',
                    }
                    
                    # Use mapping if website not in CSV
                    if not website and org_name in org_websites:
                        website = org_websites[org_name]
                    
                    # Use mapping if photo_url not in CSV
                    if not photo_url and org_name in org_photos:
                        photo_url = org_photos[org_name]
                    
                    locations.append({
                        'name': org_name,
                        'lat': lat,
                        'lon': lon,
                        'address': address,
                        'description': description,
                        'website': website,
                        'photo_url': photo_url,
                        'tags': ['LEAP', 'organization'],
                        'source_sheet': 'CSV'  # Mark as from CSV file
                    })
                except KeyError:
                    continue
                except Exception:
                    continue
            
            self.leap_locations = locations  # Store for later use
            return locations
            
        except Exception:
            return locations

    def _is_duplicate_location(self, new_location: Dict, existing_locations: List[Dict], 
                                tolerance: float = 0.0001) -> bool:
        """Check if a location is a duplicate based on name or coordinates.
        
        Args:
            new_location: The new location to check
            existing_locations: List of existing locations to check against
            tolerance: Coordinate tolerance for considering locations as duplicates (default: 0.0001 degrees)
            
        Returns:
            True if duplicate, False otherwise
        """
        new_name = new_location.get('name', '').strip().lower()
        new_lat = new_location.get('lat')
        new_lon = new_location.get('lon')
        
        for existing in existing_locations:
            existing_name = existing.get('name', '').strip().lower()
            existing_lat = existing.get('lat')
            existing_lon = existing.get('lon')
            
            # Check by name (case-insensitive)
            if new_name and existing_name and new_name == existing_name:
                return True
            
            # Check by coordinates (within tolerance)
            if (new_lat is not None and new_lon is not None and 
                existing_lat is not None and existing_lon is not None):
                if (abs(new_lat - existing_lat) < tolerance and 
                    abs(new_lon - existing_lon) < tolerance):
                    return True
        
        return False

    def load_leap_locations_from_google_sheets(self, sheet_id: str, sheet_names: List[str] = None, 
                                               use_public_export: bool = True, 
                                               credentials_path: Optional[str] = None,
                                               skip_duplicates: bool = True) -> List[Dict]:
        """Load LEAP locations from Google Sheets (supports multiple sheets).
        
        Args:
            sheet_id: Google Sheets ID (from the URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit)
            sheet_names: List of sheet names to load from. If None, loads from all sheets.
            use_public_export: If True, uses public CSV export (no auth needed, sheet must be public).
                               If False, uses gspread (requires credentials).
            credentials_path: Path to Google service account JSON credentials file (required if use_public_export=False)
            skip_duplicates: If True, skip locations that already exist in self.leap_locations
            
        Returns:
            List of location dictionaries with name, lat, lon, description, address
        """
        all_locations = []
        existing_locations = getattr(self, 'leap_locations', [])
        
        if use_public_export:
            # Method 1: Public CSV export (simpler, no authentication needed)
            # Sheet must be published to the web or publicly accessible
            try:
                if sheet_names is None:
                    # If no sheet names specified, try to get all sheets
                    # For public export, we need to know the sheet names or use gid
                    # We'll try common sheet names or the first sheet
                    sheet_names = ['Sheet1']  # Default to first sheet
                
                print(f"Attempting to load from {len(sheet_names)} sheet(s): {', '.join(sheet_names)}")
                
                for sheet_name in sheet_names:
                    print(f"Loading sheet: '{sheet_name}'...")
                    # URL format for public CSV export
                    # Properly encode sheet name (spaces, apostrophes, etc.)
                    encoded_sheet_name = quote(sheet_name)
                    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}"
                    
                    try:
                        # Read CSV directly from URL
                        df = pd.read_csv(csv_url, quotechar='"', skipinitialspace=True, on_bad_lines='skip', encoding='utf-8')
                        
                        if df.empty:
                            print(f"  Warning: Sheet '{sheet_name}' is empty")
                            continue
                        
                        print(f"  Found {len(df)} rows in sheet '{sheet_name}'")
                        locations, skipped = self._process_dataframe_to_locations(df, source_sheet=sheet_name)
                        
                        # Filter out duplicates if requested
                        if skip_duplicates:
                            new_locations = []
                            skipped_count = 0
                            for loc in locations:
                                if not self._is_duplicate_location(loc, existing_locations + all_locations):
                                    new_locations.append(loc)
                                else:
                                    skipped_count += 1
                            locations = new_locations
                            if skipped_count > 0:
                                print(f"  Skipped {skipped_count} duplicate location(s) from sheet '{sheet_name}'")
                        
                        all_locations.extend(locations)
                        print(f"  ✓ Successfully loaded {len(locations)} new locations from sheet '{sheet_name}'")
                    except Exception as e:
                        error_msg = str(e)
                        if "401" in error_msg or "Unauthorized" in error_msg:
                            print(f"Error: Sheet '{sheet_name}' is not publicly accessible (401 Unauthorized).")
                            print("   Option 1: Make the sheet public:")
                            print("     1. Open the Google Sheet")
                            print("     2. Click 'Share' button (top right)")
                            print("     3. Change access to 'Anyone with the link' → 'Viewer'")
                            print("     4. Click 'Done'")
                            print("   Option 2: Use authentication (set use_public_export=False and provide credentials_path)")
                        else:
                            print(f"Warning: Could not load sheet '{sheet_name}': {e}")
                        # Try alternative URL format (using gid instead of sheet name)
                        try:
                            # Alternative: use export format
                            csv_url_alt = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
                            df = pd.read_csv(csv_url_alt, quotechar='"', skipinitialspace=True, on_bad_lines='skip', encoding='utf-8')
                            locations, skipped = self._process_dataframe_to_locations(df, source_sheet=sheet_name)
                            
                            # Filter out duplicates if requested
                            if skip_duplicates:
                                new_locations = []
                                skipped_count = 0
                                for loc in locations:
                                    if not self._is_duplicate_location(loc, existing_locations + all_locations):
                                        new_locations.append(loc)
                                    else:
                                        skipped_count += 1
                                locations = new_locations
                                if skipped_count > 0:
                                    print(f"Skipped {skipped_count} duplicate location(s) using alternative method")
                            
                            all_locations.extend(locations)
                            print(f"Loaded {len(locations)} new locations from sheet using alternative method")
                        except Exception:
                            pass
                            
            except Exception as e:
                print(f"Error loading from Google Sheets (public export): {e}")
                return all_locations
        else:
            # Method 2: Using gspread (requires authentication, works with private sheets)
            if not HAS_GSPREAD:
                print("Error: gspread is not installed. Install it with: pip install gspread google-auth")
                return all_locations
            
            if not credentials_path:
                print("Error: credentials_path is required when use_public_export=False")
                return all_locations
            
            try:
                # Authenticate with service account
                scope = ['https://spreadsheets.google.com/feeds',
                        'https://www.googleapis.com/auth/drive']
                creds = Credentials.from_service_account_file(credentials_path, scopes=scope)
                client = gspread.authorize(creds)
                
                # Open the spreadsheet
                spreadsheet = client.open_by_key(sheet_id)
                
                # Get sheet names if not specified
                if sheet_names is None:
                    sheet_names = [sheet.title for sheet in spreadsheet.worksheets()]
                
                # Load from each sheet
                for sheet_name in sheet_names:
                    try:
                        worksheet = spreadsheet.worksheet(sheet_name)
                        # Get all values as a list of lists
                        data = worksheet.get_all_values()
                        
                        if not data:
                            continue
                        
                        # Convert to DataFrame (first row as headers)
                        headers = data[0]
                        rows = data[1:]
                        df = pd.DataFrame(rows, columns=headers)
                        
                        locations, skipped = self._process_dataframe_to_locations(df, source_sheet=sheet_name)
                        
                        # Filter out duplicates if requested
                        if skip_duplicates:
                            new_locations = []
                            skipped_count = 0
                            for loc in locations:
                                if not self._is_duplicate_location(loc, existing_locations + all_locations):
                                    new_locations.append(loc)
                                else:
                                    skipped_count += 1
                            locations = new_locations
                            if skipped_count > 0:
                                print(f"Skipped {skipped_count} duplicate location(s) from sheet '{sheet_name}'")
                        
                        all_locations.extend(locations)
                        print(f"Loaded {len(locations)} new locations from sheet '{sheet_name}'")
                    except Exception as e:
                        print(f"Warning: Could not load sheet '{sheet_name}': {e}")
                        
            except Exception as e:
                print(f"Error loading from Google Sheets (gspread): {e}")
                return all_locations
        
        # Store all locations
        if hasattr(self, 'leap_locations'):
            self.leap_locations.extend(all_locations)
        else:
            self.leap_locations = all_locations
            
        return all_locations

    def _process_dataframe_to_locations(self, df: pd.DataFrame, source_sheet: str = None) -> Tuple[List[Dict], Dict]:
        """Process a pandas DataFrame into location dictionaries.
        
        This is a helper method that processes the same format as the CSV loader.
        
        Args:
            df: DataFrame containing location data
            source_sheet: Optional name of the source sheet (for color coding)
        """
        locations = []
        
        # Drop any completely empty rows
        df = df.dropna(how='all')
        
        # Debug: Print column names for troubleshooting
        if source_sheet:
            print(f"    Columns found in '{source_sheet}': {list(df.columns)}")
            # Check if website and image columns exist
            has_website = any(col.lower() in ['website', 'url', 'link', 'web site'] for col in df.columns)
            has_image = any(col.lower() in ['images', 'image', 'photo', 'photo_url', 'img', 'picture'] for col in df.columns)
            if not has_website:
                print(f"      ⚠️  No website column found (looking for: website, url, link, web site)")
            if not has_image:
                print(f"      ⚠️  No image column found (looking for: images, image, photo, photo_url, img, picture)")
        
        skipped_reasons = {'no_name': 0, 'no_coords': 0, 'invalid_coords': 0, 'out_of_range': 0, 'other': 0}
        skipped_locations = {'no_name': [], 'no_coords': [], 'invalid_coords': [], 'out_of_range': [], 'other': []}
        
        for idx, row in df.iterrows():
            try:
                # Get organization/landmark name - try different column name variations
                # For Neighborhood Landmarks, check "LANDMARK NAME" first
                org_name = ''
                col_names_to_try = []
                
                # If it's Neighborhood Landmarks sheet, prioritize LANDMARK NAME
                if source_sheet and ('neighborhood' in source_sheet.lower() or 'landmark' in source_sheet.lower()):
                    col_names_to_try = ['LANDMARK NAME', 'Landmark Name', 'landmark name', 
                                      'ORGANIZATION NAME', 'Organization Name', 'organization name',
                                      'Name', 'name', 'ORGANIZATION', 'Organization']
                else:
                    col_names_to_try = ['ORGANIZATION NAME', 'Organization Name', 'organization name',
                                       'LANDMARK NAME', 'Landmark Name', 'landmark name',
                                       'Name', 'name', 'ORGANIZATION', 'Organization']
                
                for col_name in col_names_to_try:
                    if col_name in row:
                        org_name = str(row[col_name]).strip()
                        break
                
                if not org_name or org_name == 'nan' or org_name == '':
                    skipped_reasons['no_name'] += 1
                    skipped_locations['no_name'].append(f"Row {idx+1} (no name)")
                    continue
                
                # Parse coordinates - try different column name variations
                coords_str = ''
                for col_name in ['XY-COODRINATE', 'XY-COORDINATE', 'Coordinates', 'coordinates',
                               'COORDINATES', 'LatLon', 'latlon', 'LAT_LON', 'Latitude, Longitude',
                               'LATITUDE, LONGITUDE', 'lat, lon', 'LAT, LON']:
                    if col_name in row:
                        coords_str = str(row[col_name]).strip()
                        break
                
                if not coords_str or coords_str == 'nan' or coords_str == '':
                    skipped_reasons['no_coords'] += 1
                    skipped_locations['no_coords'].append(org_name)
                    continue
                
                # Remove quotes if present
                coords_str = coords_str.strip('"').strip("'").strip()
                
                # Split by comma and convert to float
                try:
                    lat_str, lon_str = coords_str.split(',')
                    lat = float(lat_str.strip())
                    lon = float(lon_str.strip())
                    
                    # Validate coordinates are reasonable (Pittsburgh area)
                    if not (40.0 <= lat <= 41.0) or not (-81.0 <= lon <= -79.0):
                        skipped_reasons['out_of_range'] += 1
                        skipped_locations['out_of_range'].append(org_name)
                        if source_sheet and idx < 3:  # Show first few examples
                            print(f"      Row {idx+1}: Coordinates out of range: {lat}, {lon}")
                        continue
                        
                except (ValueError, AttributeError) as e:
                    skipped_reasons['invalid_coords'] += 1
                    skipped_locations['invalid_coords'].append(org_name)
                    if source_sheet and idx < 3:  # Show first few examples
                        print(f"      Row {idx+1}: Invalid coordinate format '{coords_str}': {e}")
                    continue
                
                # Get address - try different column name variations
                address = ''
                for col_name in ['ADDRESS', 'Address', 'address']:
                    if col_name in row:
                        address = str(row[col_name]).strip()
                        break
                
                if address == 'nan':
                    address = ''
                
                # Get description - try different column name variations
                description = ''
                for col_name in ['BRIEF DESCRIPTION', 'Brief Description', 'Description', 
                               'description', 'DESCRIPTION', 'BRIEF_DESCRIPTION']:
                    if col_name in row:
                        description = str(row[col_name]).strip()
                        break
                
                if description == 'nan':
                    description = 'No description available'
                
                # Get website - try different column name variations
                # Check for website column with many variations
                website = ''
                for col_name in ['WEBSITE', 'Website', 'website', 'URL', 'url', 'WEBSITE URL', 
                               'Website URL', 'website url', 'WEB SITE', 'Web Site', 'web site',
                               'LINK', 'Link', 'link', 'WEB', 'Web', 'web']:
                    if col_name in row:
                        website = str(row[col_name]).strip()
                        break
                
                if website == 'nan' or website == '':
                    website = ''
                
                # Ensure website URL has http:// or https:// prefix
                if website and not website.startswith('http://') and not website.startswith('https://'):
                    website = 'https://' + website
                
                photo_url = ''
                # Check for images column - try many variations for ALL sheets
                # This works identically for Jaymar's list, LEAP's list, and Neighborhood Landmarks
                for col_name in ['images', 'Images', 'IMAGES', 'image', 'Image', 'IMAGE',
                               'PHOTO_URL', 'Photo URL', 'photo_url', 'Photo', 'photo',
                               'PHOTO', 'Photo', 'PICTURE', 'Picture', 'picture',
                               'IMG', 'img', 'IMG_URL', 'Img URL', 'img_url']:
                    if col_name in row:
                        photo_url = str(row[col_name]).strip()
                        break
                
                if photo_url == 'nan' or photo_url == '':
                    photo_url = ''
                
                # Convert Google Drive link to direct image URL if needed
                # This works for ALL sheets (Jaymar's list, LEAP's list, Neighborhood Landmarks)
                if photo_url and 'drive.google.com' in photo_url:
                    # Convert Google Drive sharing link to direct image URL
                    # Format: https://drive.google.com/file/d/FILE_ID/view -> https://drive.google.com/uc?export=view&id=FILE_ID
                    if '/file/d/' in photo_url:
                        file_id = photo_url.split('/file/d/')[1].split('/')[0]
                        photo_url = f'https://drive.google.com/uc?export=view&id={file_id}'
                    elif 'id=' in photo_url:
                        file_id = photo_url.split('id=')[1].split('&')[0]
                        photo_url = f'https://drive.google.com/uc?export=view&id={file_id}'
                
                # Organization mappings - applied to ALL locations regardless of source sheet
                # If website/image not found in sheet, check these mappings as fallback
                # Works for Jaymar's list, LEAP's list, and Neighborhood Landmarks
                org_websites = {
                    'Phipps Conservatory and Botanical Gardens': 'https://www.phipps.conservatory.org/',
                    'The National Opera House': 'https://www.nationaloperahouse.org/',
                    'Artists Image Resource': 'https://www.airpgh.org/',
                    'BootUP PGH': 'https://www.bootuppgh.org/',
                    'Creative Citizen Studios': 'https://www.creativecitizenstudios.org/',
                    'ARYSE (Alliance for Refugee Youth Support and Education)': 'https://www.arysepgh.org/',
                    'Saturday Light Brigade': 'https://www.slbradio.org/',
                    'Pittsburgh Center For Creative Reuse': 'https://www.pccr.org/',
                    '412 Food Rescue': 'https://www.412foodrescue.org/',
                    "Pittsburgh's Public Source": 'https://www.publicsource.org/',
                    'Casa San José': 'https://www.casasanjose.org/',
                    'Duolingo': 'https://www.duolingo.com/',
                    'YogaRoots On Location': 'https://www.yogarootsonlocation.com/',
                    'Justseeds Artists\' Cooperative': 'https://www.justseeds.org/',
                }
                
                org_photos = {
                    'Phipps Conservatory and Botanical Gardens': 'https://images.unsplash.com/photo-1416879595882-3373a0480b5b?w=800&h=600&fit=crop',
                    'The National Opera House': 'https://images.unsplash.com/photo-1503095396549-807759245b35?w=800&h=600&fit=crop',
                    'Artists Image Resource': 'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=800&h=600&fit=crop',
                    'BootUP PGH': 'https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=800&h=600&fit=crop',
                    'Creative Citizen Studios': 'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=800&h=600&fit=crop',
                    'ARYSE (Alliance for Refugee Youth Support and Education)': 'https://images.unsplash.com/photo-1503676260721-1d00da88a82c?w=800&h=600&fit=crop',
                    'Saturday Light Brigade': 'https://images.unsplash.com/photo-1478737270239-2f02b77fc618?w=800&h=600&fit=crop',
                    'Pittsburgh Center For Creative Reuse': 'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=800&h=600&fit=crop',
                    '412 Food Rescue': 'https://images.unsplash.com/photo-1542838132-92c53300491e?w=800&h=600&fit=crop',
                    "Pittsburgh's Public Source": 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&h=600&fit=crop',
                    'Casa San José': 'https://images.unsplash.com/photo-1503676260721-1d00da88a82c?w=800&h=600&fit=crop',
                    'Duolingo': 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=800&h=600&fit=crop',
                    'YogaRoots On Location': 'https://images.unsplash.com/photo-1506126613408-eca07ce68773?w=800&h=600&fit=crop',
                    'Justseeds Artists\' Cooperative': 'https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=800&h=600&fit=crop',
                }
                
                # Use mapping if website not in sheet - works for ALL sheets (Jaymar's, LEAP's, Neighborhood Landmarks)
                if not website and org_name in org_websites:
                    website = org_websites[org_name]
                
                # Use mapping if photo_url not in sheet - works for ALL sheets (Jaymar's, LEAP's, Neighborhood Landmarks)
                if not photo_url and org_name in org_photos:
                    photo_url = org_photos[org_name]
                
                # Determine tags based on source sheet
                tags = ['LEAP', 'organization']
                if source_sheet:
                    # Add source sheet to tags for identification
                    tags.append(source_sheet.lower().replace("'", "").replace(" ", "_"))
                
                # Debug: Print if website/image found for troubleshooting
                if source_sheet and ('jaymar' in source_sheet.lower() or "jaymar's" in source_sheet.lower()):
                    if website:
                        print(f"      Found website for '{org_name}': {website}")
                    else:
                        print(f"      No website found for '{org_name}'")
                    if photo_url:
                        print(f"      Found image for '{org_name}': {photo_url[:50]}...")
                    else:
                        print(f"      No image found for '{org_name}'")
                
                locations.append({
                    'name': org_name,
                    'lat': lat,
                    'lon': lon,
                    'address': address,
                    'description': description,
                    'website': website,
                    'photo_url': photo_url,
                    'tags': tags,
                    'source_sheet': source_sheet  # Store source sheet for color coding
                })
            except KeyError as e:
                skipped_reasons['other'] += 1
                # Try to get name for error reporting
                try:
                    org_name = ''
                    for col_name in ['ORGANIZATION NAME', 'LANDMARK NAME', 'Name', 'name']:
                        if col_name in row:
                            org_name = str(row[col_name]).strip()
                            break
                    if org_name and org_name != 'nan':
                        skipped_locations['other'].append(org_name)
                    else:
                        skipped_locations['other'].append(f"Row {idx+1}")
                except:
                    skipped_locations['other'].append(f"Row {idx+1}")
                if source_sheet and idx < 3:
                    print(f"      Row {idx+1}: KeyError: {e}")
                continue
            except Exception as e:
                skipped_reasons['other'] += 1
                # Try to get name for error reporting
                try:
                    org_name = ''
                    for col_name in ['ORGANIZATION NAME', 'LANDMARK NAME', 'Name', 'name']:
                        if col_name in row:
                            org_name = str(row[col_name]).strip()
                            break
                    if org_name and org_name != 'nan':
                        skipped_locations['other'].append(org_name)
                    else:
                        skipped_locations['other'].append(f"Row {idx+1}")
                except:
                    skipped_locations['other'].append(f"Row {idx+1}")
                if source_sheet and idx < 3:
                    print(f"      Row {idx+1}: Error: {e}")
                continue
        
        # Print summary of skipped rows if any were skipped
        if source_sheet and sum(skipped_reasons.values()) > 0:
            total_skipped = sum(skipped_reasons.values())
            print(f"    Skipped {total_skipped} row(s) from '{source_sheet}':")
            if skipped_reasons['no_name'] > 0:
                print(f"      - {skipped_reasons['no_name']} missing organization/landmark name")
            if skipped_reasons['no_coords'] > 0:
                print(f"      - {skipped_reasons['no_coords']} missing coordinates:")
                for name in skipped_locations['no_coords']:
                    print(f"        • {name}")
            if skipped_reasons['invalid_coords'] > 0:
                print(f"      - {skipped_reasons['invalid_coords']} invalid coordinate format:")
                for name in skipped_locations['invalid_coords']:
                    print(f"        • {name}")
            if skipped_reasons['out_of_range'] > 0:
                print(f"      - {skipped_reasons['out_of_range']} coordinates outside Pittsburgh area:")
                for name in skipped_locations['out_of_range']:
                    print(f"        • {name}")
            if skipped_reasons['other'] > 0:
                print(f"      - {skipped_reasons['other']} other errors:")
                for name in skipped_locations['other']:
                    print(f"        • {name}")
        
        return locations, skipped_locations

    def add_leap_locations(self):
        """Add LEAP locations to the map with color-coded icons based on source sheet.
        Colors: Red for Neighborhood landmarks, Blue for Jaymar's list, Green for LEAP locations.
        """
        if not hasattr(self, 'leap_locations') or not self.leap_locations:
            return
        
        # Color mapping based on source sheet name (case-insensitive)
        def get_marker_color(source_sheet):
            if not source_sheet:
                return 'green'  # Default to green
            
            source_lower = source_sheet.lower()
            # Check for neighborhood landmarks (red)
            if 'neigbourhood' in source_lower or 'neighborhood' in source_lower or 'landmark' in source_lower:
                return 'red'
            # Check for Jaymar's list (blue)
            elif 'jaymar' in source_lower or "jaymar's" in source_lower:
                return 'blue'
            # Check for LEAP's list (green)
            elif "leap's" in source_lower or 'leap' in source_lower:
                return 'green'
            else:
                return 'green'  # Default to green
        
        for location in self.leap_locations:
            try:
                # Validate location data
                if 'lat' not in location or 'lon' not in location:
                    continue
                
                lat = location['lat']
                lon = location['lon']
                name = location.get('name', 'LEAP Location')
                source_sheet = location.get('source_sheet', '')
                
                # Get photo source if available (same pattern as landmarks)
                photo_src = self._get_image_src(location.get('photo_url')) if location.get('photo_url') else None
                photo_url_original = location.get('photo_url', '')
                
                # Check if this is a Neighborhood Landmark (for larger image display)
                is_neighborhood_landmark = source_sheet and ('neighborhood' in source_sheet.lower() or 'landmark' in source_sheet.lower())
                
                # Create popup content with HTML
                # For Neighborhood Landmarks, show larger image since it's used as the marker icon
                image_html = ''
                if photo_src:
                    if is_neighborhood_landmark:
                        # Larger image for Neighborhood Landmarks (since icon is the image)
                        image_html = f'''
                        <div style="margin-bottom: 10px;">
                            <img src="{photo_src}" 
                                 style="width: 100%; max-height: 300px; object-fit: cover; border-radius: 5px; cursor: pointer;" 
                                 alt="{name}" 
                                 loading="lazy" 
                                 decoding="async"
                                 onclick="window.open('{photo_url_original if photo_url_original else photo_src}', '_blank')"
                                 onerror="this.onerror=null;this.src='https://via.placeholder.com/400x300/cccccc/000000?text=Image+Unavailable';"
                                 title="Click to view full image">
                            <p style="font-size: 11px; color: #999; margin-top: 5px; text-align: center;">Click image to view full size</p>
                        </div>
                        '''
                    else:
                        # Standard size for other locations (Jaymar's list, LEAP's list)
                        # Make images clickable to view full size
                        image_html = f'''
                        <div style="margin-bottom: 10px;">
                            <img src="{photo_src}" 
                                 style="width: 100%; height: 150px; object-fit: cover; border-radius: 5px; cursor: pointer;" 
                                 alt="{name}" 
                                 loading="lazy" 
                                 decoding="async"
                                 onclick="window.open('{photo_url_original if photo_url_original else photo_src}', '_blank')"
                                 onerror="this.onerror=null;this.src='https://via.placeholder.com/400x300/cccccc/000000?text=Image+Unavailable';"
                                 title="Click to view full image">
                            <p style="font-size: 11px; color: #999; margin-top: 5px; text-align: center;">Click image to view full size</p>
                        </div>
                        '''
                
                popup_html = f"""
                <div style="width: 300px;">
                    <h3 style="color: #2c3e50; margin-bottom: 10px;">{name}</h3>
                    {f'<p style="margin-bottom: 8px; font-size: 12px; color: #666;"><strong>Address:</strong> {location["address"]}</p>' if location.get('address') else ''}
                    <p style="margin-bottom: 10px; font-size: 14px;">{location['description']}</p>
                    
                    <div style="margin-bottom: 10px;">
                        <strong>Tags:</strong> {', '.join(location['tags'])}
                    </div>
                    {f'<div style="margin-bottom: 8px; font-size: 12px; color: #666;"><strong>Source:</strong> {source_sheet}</div>' if source_sheet else ''}
                    
                    {image_html}
                    
                    {f'<div style="text-align: center;"><a href="{location["website"]}" target="_blank" style="background-color: #3498db; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; display: inline-block;">Visit Website</a></div>' if location.get('website') else ''}
                </div>
                """
                
                # Get color based on source sheet
                marker_color = get_marker_color(source_sheet)
                
                # For Neighborhood Landmarks, use custom image as marker icon if available
                # The image appears as a small icon on the map, and clicking shows the full image in popup
                marker_icon = None
                
                if is_neighborhood_landmark and location.get('photo_url'):
                    # Use custom image as marker icon for Neighborhood Landmarks
                    try:
                        # Get the image URL (already converted from Google Drive if needed)
                        marker_image_url = location.get('photo_url')
                        
                        # Download and cache the image first, then get the local file path
                        # This ensures the image is available locally for CustomIcon
                        import hashlib
                        import os
                        
                        # Create deterministic filename for caching
                        guessed_ext = os.path.splitext(marker_image_url.split('?')[0])[1].lower()
                        if guessed_ext not in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                            guessed_ext = '.jpg'
                        name = hashlib.sha256(marker_image_url.encode('utf-8')).hexdigest() + guessed_ext
                        local_path = os.path.join(self.image_cache_dir, name)
                        
                        # Download image if not cached
                        if not os.path.exists(local_path):
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                                'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
                            }
                            try:
                                resp = requests.get(marker_image_url, headers=headers, timeout=15, allow_redirects=True)
                                if resp.ok and resp.content:
                                    with open(local_path, 'wb') as f:
                                        f.write(resp.content)
                            except Exception as e:
                                print(f"      Warning: Could not download image for '{name}': {e}")
                                marker_icon = folium.Icon(color=marker_color, icon='info-sign')
                                local_path = None
                        
                        # Use local file path for CustomIcon (more reliable than URLs)
                        if local_path and os.path.exists(local_path):
                            # Use relative path from the HTML file location
                            # The HTML file will be in the project root, images in files/images/
                            icon_image_path = os.path.relpath(local_path, os.getcwd())
                            
                            # Create custom icon with the local image file
                            # This makes the image appear as a small icon/marker on the map
                            marker_icon = folium.CustomIcon(
                                icon_image=icon_image_path,
                                icon_size=(70, 70),  # Size of the marker icon (width, height) - increased for better visibility
                                icon_anchor=(35, 70),  # Anchor point (center bottom - bottom center touches the location)
                                popup_anchor=(0, -70)  # Popup appears above the icon
                            )
                        else:
                            # Fallback to URL if local file not available
                            marker_icon = folium.CustomIcon(
                                icon_image=marker_image_url,
                                icon_size=(70, 70),  # Increased size for better visibility
                                icon_anchor=(35, 70),
                                popup_anchor=(0, -70)
                            )
                    except Exception as e:
                        # Fall back to default icon if image fails
                        print(f"      Warning: Could not use custom image as icon for '{name}': {e}")
                        marker_icon = folium.Icon(color=marker_color, icon='info-sign')
                
                # Use default icon if no custom image
                if not marker_icon:
                    marker_icon = folium.Icon(color=marker_color, icon='info-sign')
                
                # Add marker with custom icon or color-coded icon
                marker = folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=350),
                    tooltip=name,
                    icon=marker_icon
                )
                marker.add_to(self.leap_group)
            except Exception:
                continue

    def add_custom_locations(self, locations: List[Dict]):
        """Add custom locations provided by the user."""
        for location in locations:
            photo_src = self._get_image_src(location.get('photo_url')) if location.get('photo_url') else None
            popup_html = f"""
            <div style="width: 300px;">
                <h3 style="color: #2c3e50; margin-bottom: 10px;">{location.get('name', 'Custom Location')}</h3>
                <p style="margin-bottom: 10px; font-size: 14px;">{location.get('description', 'No description available')}</p>
                
                {f'<div style="margin-bottom: 10px;"><strong>Tags:</strong> {", ".join(location.get("tags", []))}</div>' if location.get('tags') else ''}
                
                {f'<div style="margin-bottom: 10px;"><img src="{photo_src}" style="width: 100%; height: 150px; object-fit: cover; border-radius: 5px;" alt="{location.get("name", "Custom Location")}" loading="lazy" decoding="async" referrerpolicy="no-referrer" crossorigin="anonymous" onerror="this.onerror=null;this.src=&quot;https://via.placeholder.com/400x300/cccccc/000000?text=Image+Unavailable&quot;;"></div>' if photo_src else ''}
                
                {f'<div style="text-align: center;"><a href="{location["website"]}" target="_blank" style="background-color: #3498db; color: white; padding: 8px 16px; text-decoration: none; border-radius: 5px; display: inline-block;">Visit Website</a></div>' if location.get('website') else ''}
            </div>
            """
            
            folium.Marker(
                location=[location['lat'], location['lon']],
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=location.get('name', 'Custom Location'),
                icon=folium.Icon(color='green', icon='star')
            ).add_to(self.custom_group)

    def add_marker_clustering(self):
        """Cluster markers to improve performance and UX."""
        cluster = plugins.MarkerCluster(name='Clustered Locations', show=False)
        # Move existing markers from groups into a cluster clone for optional view
        for group in [self.landmarks_group, self.custom_group, self.leap_group]:
            # group._children is internal; iterate safely over a copy
            for key, child in list(group._children.items()):
                if isinstance(child, folium.map.Marker):
                    # Duplicate a marker into the cluster (keep original in group for layer toggling)
                    folium.Marker(
                        location=child.location,
                        popup=child.options.get('popup') if hasattr(child, 'options') else None,
                        tooltip=child.options.get('tooltip') if hasattr(child, 'options') else None,
                        icon=child.icon if hasattr(child, 'icon') else None
                    ).add_to(cluster)
        cluster.add_to(self.map)

    def _get_image_src(self, url: Optional[str], use_base64: bool = True) -> str:
        """Return a base64-encoded data URI for the image, or original URL as fallback.
        This works perfectly for local HTML files without needing file:// URLs.
        
        Args:
            url: Image URL to download and encode
            use_base64: If True, embed as base64 data URI (recommended for local HTML)
        """
        if not url:
            return 'https://via.placeholder.com/400x300/cccccc/000000?text=Image+Unavailable'
        
        if not use_base64:
            return url
        
        try:
            # Create deterministic filename for caching
            guessed_ext = os.path.splitext(url.split('?')[0])[1].lower()
            if guessed_ext not in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
                guessed_ext = '.jpg'
            name = hashlib.sha256(url.encode('utf-8')).hexdigest() + guessed_ext
            local_path = os.path.join(self.image_cache_dir, name)
            
            # Download image if not cached
            image_data = None
            mime_type = 'image/jpeg'
            
            if os.path.exists(local_path):
                # Read from cache
                with open(local_path, 'rb') as f:
                    image_data = f.read()
                # Determine MIME type from extension
                if name.endswith('.png'):
                    mime_type = 'image/png'
                elif name.endswith('.webp'):
                    mime_type = 'image/webp'
                elif name.endswith('.gif'):
                    mime_type = 'image/gif'
            else:
                # Download image
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
                    'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
                    'Referer': 'https://unsplash.com/',
                }
                try:
                    resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                    if resp.ok and resp.content:
                        image_data = resp.content
                        # Determine MIME type from content-type header
                        content_type = resp.headers.get('Content-Type', '').lower()
                        if 'image/png' in content_type:
                            mime_type = 'image/png'
                            name = hashlib.sha256(url.encode('utf-8')).hexdigest() + '.png'
                            local_path = os.path.join(self.image_cache_dir, name)
                        elif 'image/webp' in content_type:
                            mime_type = 'image/webp'
                            name = hashlib.sha256(url.encode('utf-8')).hexdigest() + '.webp'
                            local_path = os.path.join(self.image_cache_dir, name)
                        elif 'image/gif' in content_type:
                            mime_type = 'image/gif'
                            name = hashlib.sha256(url.encode('utf-8')).hexdigest() + '.gif'
                            local_path = os.path.join(self.image_cache_dir, name)
                        
                        # Cache the image
                        with open(local_path, 'wb') as f:
                            f.write(image_data)
                    else:
                        return url
                except requests.exceptions.RequestException:
                    return url
            
            # Convert to base64 data URI
            if image_data:
                try:
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                    full_data_uri = f'data:{mime_type};base64,{base64_data}'
                    return full_data_uri
                except Exception:
                    return url
            else:
                return url
                
        except Exception:
            return url

    def add_heatmap(self):
        """Add a heatmap layer of all points."""
        points: List[Tuple[float, float]] = []
        # Skip hardcoded landmarks - using only Google Sheets locations
        # for lm in self.landmarks:
        #     points.append((lm['lat'], lm['lon']))
        # Include any custom locations already attached via groups
        if hasattr(self, 'custom_group'):
            for key, child in list(self.custom_group._children.items()):
                if isinstance(child, folium.map.Marker):
                    lat, lon = child.location
                    points.append((lat, lon))
        # Include LEAP locations
        if hasattr(self, 'leap_group'):
            for key, child in list(self.leap_group._children.items()):
                if isinstance(child, folium.map.Marker):
                    lat, lon = child.location
                    points.append((lat, lon))
        if points:
            plugins.HeatMap(points, name='Heatmap', show=False, radius=18, blur=22, min_opacity=0.3).add_to(self.map)

    def add_minimap(self):
        """Add a minimap overview control."""
        plugins.MiniMap(toggle_display=True).add_to(self.map)

    def add_geolocation(self):
        """Add a control to locate the user's position."""
        plugins.LocateControl(auto_start=False, flyTo=True).add_to(self.map)

    def add_layer_control(self):
        """Add layer control to toggle between different map layers."""
        folium.LayerControl().add_to(self.map)

    def add_measurement_tools(self):
        """Add measurement tools for distance and area calculations."""
        plugins.MeasureControl().add_to(self.map)

    def add_fullscreen_button(self):
        """Add fullscreen button for better map viewing."""
        plugins.Fullscreen().add_to(self.map)

    def add_draw_tools(self):
        """Add draw/edit tools for user annotations."""
        plugins.Draw(export=True, position='topleft').add_to(self.map)

    def add_mouse_position(self):
        """Show mouse cursor latitude/longitude."""
        plugins.MousePosition(position='bottomleft', separator=' | ', prefix='Lat/Lon:').add_to(self.map)

    def add_search_and_filter(self):
        """Add teen-friendly search and filter controls to the map."""
        # Build location data for JavaScript (more reliable than parsing DOM)
        locations_data = []
        
        # Skip hardcoded landmarks - using only Google Sheets locations
        # Add landmarks
        # for lm in self.landmarks:
        #     locations_data.append({
        #         'name': lm['name'],
        #         'lat': lm['lat'],
        #         'lon': lm['lon'],
        #         'tags': lm.get('tags', []),
        #         'type': 'landmark'
        #     })
        
        # Add LEAP locations
        if hasattr(self, 'leap_locations') and self.leap_locations:
            for loc in self.leap_locations:
                locations_data.append({
                    'name': loc.get('name', ''),
                    'lat': loc.get('lat', 0),
                    'lon': loc.get('lon', 0),
                    'tags': loc.get('tags', []),
                    'type': 'leap'
                })
        
        # Collect all unique tags
        all_tags = set()
        for loc in locations_data:
            all_tags.update(loc.get('tags', []))
        
        # Convert to JSON for JavaScript
        locations_json = json.dumps(locations_data)
        
        # Create teen-friendly tag names
        tag_display_names = {
            'park': '🌳 Parks & Nature',
            'history': '🏛️ History',
            'rivers': '🌊 Rivers',
            'monument': '🗽 Monuments',
            'university': '🎓 Schools & Universities',
            'education': '📚 Education',
            'research': '🔬 Research',
            'technology': '💻 Technology',
            'architecture': '🏗️ Architecture',
            'sports': '⚽ Sports',
            'baseball': '⚾ Baseball',
            'football': '🏈 Football',
            'stadium': '🏟️ Stadiums',
            'entertainment': '🎬 Entertainment',
            'museum': '🖼️ Museums',
            'art': '🎨 Art',
            'culture': '🎭 Culture',
            'garden': '🌺 Gardens',
            'nature': '🌿 Nature',
            'conservatory': '🌱 Conservatories',
            'transportation': '🚇 Transportation',
            'views': '👀 Scenic Views',
            'tourist': '📸 Tourist Spots',
            'LEAP': '⭐ LEAP Organizations',
            'organization': '🏢 Organizations',
            'custom': '📍 Custom Locations'
        }
        
        # Build filter HTML
        filter_buttons = ''
        for tag in sorted(all_tags):
            display_name = tag_display_names.get(tag, tag.title())
            filter_buttons += f'''
            <button class="filter-btn" data-tag="{tag}" onclick="toggleFilter('{tag}')">
                {display_name}
            </button>
            '''
        
        # Add search and filter UI
        search_filter_html = f'''
        <div id="search-filter-panel" style="
            position: fixed;
            top: 10px;
            left: 10px;
            width: 320px;
            max-height: 90vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            z-index: 1000;
            overflow-y: auto;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
        ">
            <div style="
                color: white;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 15px;
                text-align: center;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            ">
                🔍 Find Places
            </div>
            
            <div style="margin-bottom: 20px; position: relative;">
                <input 
                    type="text" 
                    id="search-box" 
                    placeholder="🔎 Search locations..." 
                    style="
                        width: 100%;
                        padding: 12px;
                        border: none;
                        border-radius: 10px;
                        font-size: 16px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        outline: none;
                    "
                    onkeyup="handleSearchInput(event)"
                    onfocus="showSuggestions()"
                    onblur="setTimeout(() => hideSuggestions(), 200)"
                />
                <div id="search-suggestions" style="
                    display: none;
                    position: absolute;
                    top: 100%;
                    left: 0;
                    right: 0;
                    background: white;
                    border-radius: 10px;
                    margin-top: 5px;
                    max-height: 300px;
                    overflow-y: auto;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                    z-index: 1001;
                ">
                </div>
            </div>
            
            <div style="margin-bottom: 15px;">
                <div style="
                    color: white;
                    font-size: 18px;
                    font-weight: 600;
                    margin-bottom: 10px;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
                ">
                    Filter by Category:
                </div>
                <div id="filter-buttons" style="
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px;
                ">
                    {filter_buttons}
                </div>
            </div>
            
            <div style="
                background: rgba(255,255,255,0.2);
                border-radius: 10px;
                padding: 12px;
                margin-top: 15px;
            ">
                <div style="color: white; font-weight: 600; margin-bottom: 8px;">
                    Quick Filters:
                </div>
                <button 
                    class="quick-filter-btn" 
                    onclick="showAllLocations()"
                    style="
                        width: 100%;
                        padding: 10px;
                        margin: 5px 0;
                        background: rgba(255,255,255,0.9);
                        border: none;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: 600;
                        cursor: pointer;
                        transition: all 0.3s;
                    "
                    onmouseover="this.style.background='white'; this.style.transform='scale(1.02)'"
                    onmouseout="this.style.background='rgba(255,255,255,0.9)'; this.style.transform='scale(1)'"
                >
                    👁️ Show All
                </button>
                <button 
                    class="quick-filter-btn" 
                    onclick="showOnlyLandmarks()"
                    style="
                        width: 100%;
                        padding: 10px;
                        margin: 5px 0;
                        background: rgba(255,255,255,0.9);
                        border: none;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: 600;
                        cursor: pointer;
                        transition: all 0.3s;
                    "
                    onmouseover="this.style.background='white'; this.style.transform='scale(1.02)'"
                    onmouseout="this.style.background='rgba(255,255,255,0.9)'; this.style.transform='scale(1)'"
                >
                    🏛️ Landmarks Only
                </button>
                <button 
                    class="quick-filter-btn" 
                    onclick="showOnlyLEAP()"
                    style="
                        width: 100%;
                        padding: 10px;
                        margin: 5px 0;
                        background: rgba(255,255,255,0.9);
                        border: none;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: 600;
                        cursor: pointer;
                        transition: all 0.3s;
                    "
                    onmouseover="this.style.background='white'; this.style.transform='scale(1.02)'"
                    onmouseout="this.style.background='rgba(255,255,255,0.9)'; this.style.transform='scale(1)'"
                >
                    ⭐ LEAP Only
                </button>
            </div>
            
            <div id="results-count" style="
                color: white;
                text-align: center;
                margin-top: 15px;
                font-size: 14px;
                font-weight: 500;
            ">
                Showing all locations
            </div>
        </div>
        
        <style>
            .filter-btn {{
                padding: 8px 12px;
                margin: 4px;
                background: rgba(255,255,255,0.9);
                border: 2px solid transparent;
                border-radius: 20px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                color: #333;
            }}
            
            .filter-btn:hover {{
                background: white;
                transform: scale(1.05);
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }}
            
            .filter-btn.active {{
                background: #ffd700;
                border-color: #ffed4e;
                color: #000;
                box-shadow: 0 4px 12px rgba(255,215,0,0.4);
            }}
            
            #search-filter-panel::-webkit-scrollbar {{
                width: 8px;
            }}
            
            #search-filter-panel::-webkit-scrollbar-track {{
                background: rgba(255,255,255,0.1);
                border-radius: 10px;
            }}
            
            #search-filter-panel::-webkit-scrollbar-thumb {{
                background: rgba(255,255,255,0.3);
                border-radius: 10px;
            }}
            
            #search-filter-panel::-webkit-scrollbar-thumb:hover {{
                background: rgba(255,255,255,0.5);
            }}
            
            #search-suggestions::-webkit-scrollbar {{
                width: 6px;
            }}
            
            #search-suggestions::-webkit-scrollbar-track {{
                background: #f1f1f1;
                border-radius: 10px;
            }}
            
            #search-suggestions::-webkit-scrollbar-thumb {{
                background: #888;
                border-radius: 10px;
            }}
            
            #search-suggestions::-webkit-scrollbar-thumb:hover {{
                background: #555;
            }}
            
            .suggestion-item:last-child {{
                border-bottom: none !important;
            }}
        </style>
        
        <script>
            // Location data injected from Python
            const LOCATIONS_DATA = {locations_json};
            
            let activeFilters = new Set();
            let foliumMap = null;
            let allLocations = LOCATIONS_DATA || [];
            let isInitialized = false;
            let markerMap = {{}}; // Map location names to actual markers
            
            // Find the map object
            function findMap() {{
                // Method 1: Global map variable (Folium default)
                if (typeof map !== 'undefined' && map && typeof map.getZoom === 'function') {{
                    return map;
                }}
                // Method 2: Window.map
                if (typeof window !== 'undefined' && window.map && typeof window.map.getZoom === 'function') {{
                    return window.map;
                }}
                // Method 3: Find via Leaflet container
                if (typeof L !== 'undefined') {{
                    let container = document.querySelector('.leaflet-container');
                    if (container && L.map && L.map._instances) {{
                        for (let id in L.map._instances) {{
                            let instance = L.map._instances[id];
                            if (instance && instance.getContainer && instance.getContainer() === container) {{
                                return instance;
                            }}
                        }}
                        if (container._leaflet_id) {{
                            return L.map._instances[container._leaflet_id];
                        }}
                    }}
                }}
                return null;
            }}
            
            // Initialize and find markers
            function initSearchFilter() {{
                if (isInitialized) return;
                
                foliumMap = findMap();
                if (!foliumMap) {{
                    setTimeout(initSearchFilter, 300);
                    return;
                }}
                
                isInitialized = true;
                
                // Find markers by matching coordinates
                foliumMap.eachLayer(function(layer) {{
                    if (layer instanceof L.Marker) {{
                        let lat = layer.getLatLng().lat;
                        let lng = layer.getLatLng().lng;
                        
                        // Find matching location in our data
                        for (let i = 0; i < allLocations.length; i++) {{
                            let loc = allLocations[i];
                            let locLng = loc.lon || loc.lng;
                            if (Math.abs(loc.lat - lat) < 0.0001 && Math.abs(locLng - lng) < 0.0001) {{
                                allLocations[i].marker = layer;
                                markerMap[loc.name] = layer;
                                break;
                            }}
                        }}
                    }} else if (layer instanceof L.LayerGroup || layer instanceof L.FeatureGroup) {{
                        layer.eachLayer(function(sublayer) {{
                            if (sublayer instanceof L.Marker) {{
                                let lat = sublayer.getLatLng().lat;
                                let lng = sublayer.getLatLng().lng;
                                
                                for (let i = 0; i < allLocations.length; i++) {{
                                    let loc = allLocations[i];
                                    let locLng = loc.lon || loc.lng;
                                    if (Math.abs(loc.lat - lat) < 0.0001 && Math.abs(locLng - lng) < 0.0001) {{
                                        allLocations[i].marker = sublayer;
                                        markerMap[loc.name] = sublayer;
                                        break;
                                    }}
                                }}
                            }}
                        }});
                    }}
                }});
                
                updateResultsCount(allLocations.length);
            }}
            
            // Start initialization
            function startInit() {{
                if (typeof L === 'undefined') {{
                    setTimeout(startInit, 100);
                    return;
                }}
                
                initSearchFilter();
                
                if (document.readyState === 'loading') {{
                    document.addEventListener('DOMContentLoaded', function() {{
                        setTimeout(initSearchFilter, 1000);
                    }});
                }} else {{
                    setTimeout(initSearchFilter, 1000);
                }}
            }}
            
            startInit();
            
            window.addEventListener('load', function() {{
                setTimeout(initSearchFilter, 1500);
            }});
            
            function handleSearchInput(event) {{
                let searchTerm = document.getElementById('search-box').value;
                
                // Always show suggestions as user types
                showSuggestions();
                
                if (event.key === 'Enter' && searchTerm.trim()) {{
                    // Navigate to first matching location
                    let matches = getMatchingLocations(searchTerm);
                    if (matches.length > 0) {{
                        navigateToLocation(matches[0]);
                        hideSuggestions();
                    }}
                }} else {{
                    // Filter markers as user types
                    performSearch();
                }}
            }}
            
            function getMatchingLocations(searchTerm) {{
                if (!searchTerm || searchTerm.length < 1) {{
                    return [];
                }}
                
                let term = searchTerm.toLowerCase();
                return allLocations.filter(function(loc) {{
                    let name = (loc.name || '').toLowerCase();
                    return name.includes(term);
                }}).slice(0, 8); // Limit to 8 suggestions
            }}
            
            let currentSuggestions = [];
            
            function showSuggestions() {{
                let searchTerm = document.getElementById('search-box').value;
                let suggestionsDiv = document.getElementById('search-suggestions');
                
                if (!searchTerm || searchTerm.length < 1) {{
                    suggestionsDiv.style.display = 'none';
                    currentSuggestions = [];
                    return;
                }}
                
                let matches = getMatchingLocations(searchTerm);
                currentSuggestions = matches;
                
                if (matches.length === 0) {{
                    suggestionsDiv.style.display = 'none';
                    return;
                }}
                
                let html = '';
                matches.forEach(function(loc, index) {{
                    let icon = loc.type === 'leap' ? '⭐' : '🏛️';
                    let typeLabel = loc.type === 'leap' ? 'LEAP' : 'Landmark';
                    html += `
                        <div class="suggestion-item" 
                             onclick="navigateToLocationByIndex(${{index}})"
                             style="
                                padding: 12px;
                                cursor: pointer;
                                border-bottom: 1px solid #eee;
                                transition: background 0.2s;
                             "
                             onmouseover="this.style.background='#f0f0f0'"
                             onmouseout="this.style.background='white'"
                        >
                            <div style="font-weight: 600; color: #333; margin-bottom: 4px;">
                                ${{icon}} ${{loc.name}}
                            </div>
                            <div style="font-size: 12px; color: #666;">
                                ${{typeLabel}}
                            </div>
                        </div>
                    `;
                }});
                
                suggestionsDiv.innerHTML = html;
                suggestionsDiv.style.display = 'block';
            }}
            
            function navigateToLocationByIndex(index) {{
                if (currentSuggestions && currentSuggestions[index]) {{
                    navigateToLocation(currentSuggestions[index]);
                }}
            }}
            
            function hideSuggestions() {{
                document.getElementById('search-suggestions').style.display = 'none';
            }}
            
            function navigateToLocation(location) {{
                if (!foliumMap && !isInitialized) {{
                    initSearchFilter();
                    setTimeout(function() {{ navigateToLocation(location); }}, 500);
                    return;
                }}
                
                if (!foliumMap) {{
                    foliumMap = findMap();
                    if (!foliumMap) {{
                        setTimeout(function() {{ navigateToLocation(location); }}, 300);
                        return;
                    }}
                }}
                
                // Handle both 'lon' and 'lng' field names
                let lat = location.lat;
                let lng = location.lon || location.lng;
                
                if (!location || !lat || !lng) {{
                    return;
                }}
                
                // Close any open popups first
                foliumMap.closePopup();
                
                // Get the marker if we haven't found it yet
                if (!location.marker && markerMap[location.name]) {{
                    location.marker = markerMap[location.name];
                }}
                
                // Zoom to exact location with higher zoom level for precision
                let zoomLevel = 17; // Higher zoom for exact location
                
                // Use flyTo for smooth animation if available
                if (foliumMap.flyTo) {{
                    foliumMap.flyTo([lat, lng], zoomLevel, {{
                        animate: true,
                        duration: 1.2
                    }});
                }} else {{
                    foliumMap.setView([lat, lng], zoomLevel, {{
                        animate: true,
                        duration: 0.6
                    }});
                }}
                
                // Open popup after zoom completes - wait for animation
                setTimeout(function() {{
                    // Ensure we're at the exact location
                    foliumMap.setView([lat, lng], zoomLevel);
                    
                    // Try to open the marker's popup
                    if (location.marker && typeof location.marker.openPopup === 'function') {{
                        try {{
                            // Small delay to ensure map is ready
                            setTimeout(function() {{
                                location.marker.openPopup();
                            }}, 100);
                        }} catch(e) {{
                            // If popup fails, at least we're at the location
                        }}
                    }}
                }}, 1300);
                
                // Update search box
                let searchBox = document.getElementById('search-box');
                if (searchBox) {{
                    searchBox.value = location.name || '';
                }}
                hideSuggestions();
            }}
            
            function performSearch() {{
                if (!isInitialized) {{
                    initSearchFilter();
                    return;
                }}
                
                let searchTerm = document.getElementById('search-box').value.toLowerCase();
                let visibleCount = 0;
                
                allLocations.forEach(function(loc) {{
                    let name = (loc.name || '').toLowerCase();
                    let matchesSearch = !searchTerm || name.includes(searchTerm);
                    
                    let matchesFilter = activeFilters.size === 0;
                    if (activeFilters.size > 0) {{
                        let tags = loc.tags || [];
                        matchesFilter = tags.some(tag => activeFilters.has(tag.toLowerCase()));
                    }}
                    
                    if (matchesSearch && matchesFilter) {{
                        visibleCount++;
                    }}
                }});
                
                updateResultsCount(visibleCount);
            }}
            
            function toggleFilter(tag) {{
                let btn = document.querySelector(`[data-tag="${{tag}}"]`);
                if (activeFilters.has(tag)) {{
                    activeFilters.delete(tag);
                    btn.classList.remove('active');
                }} else {{
                    activeFilters.add(tag);
                    btn.classList.add('active');
                }}
                performSearch();
            }}
            
            function showAllLocations() {{
                activeFilters.clear();
                document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
                document.getElementById('search-box').value = '';
                performSearch();
            }}
            
            function showOnlyLandmarks() {{
                activeFilters.clear();
                document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
                document.getElementById('search-box').value = '';
                let count = allLocations.filter(loc => loc.type === 'landmark').length;
                updateResultsCount(count);
            }}
            
            function showOnlyLEAP() {{
                activeFilters.clear();
                document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
                document.getElementById('search-box').value = '';
                let count = allLocations.filter(loc => loc.type === 'leap').length;
                updateResultsCount(count);
            }}
            
            function updateResultsCount(count) {{
                let total = allLocations.length;
                if (total > 0) {{
                    document.getElementById('results-count').textContent = 
                        `Showing ${{count}} of ${{total}} locations`;
                }}
            }}
        </script>
        '''
        
        self.map.get_root().html.add_child(folium.Element(search_filter_html))

    def save_map(self, filename: str = 'pittsburgh_interactive_map.html'):
        """Save the map to an HTML file."""
        if self.map:
            self.map.save(filename)
            return filename
        else:
            return None

    def _build_geojson(self, custom_locations: List[Dict] = None) -> Dict:
        """Build a GeoJSON FeatureCollection from landmarks, custom locations, and LEAP locations."""
        features: List[Dict] = []
        # Skip hardcoded landmarks - using only Google Sheets locations
        # for lm in self.landmarks:
        #     features.append({
        #         "type": "Feature",
        #         "properties": {
        #             "name": lm['name'],
        #             "description": lm['description'],
        #             "website": lm['website'],
        #             "tags": lm['tags'],
        #             "photo_url": lm.get('photo_url', ''),
        #             "kind": "landmark"
        #         },
        #         "geometry": {"type": "Point", "coordinates": [lm['lon'], lm['lat']]}
        #     })
        if custom_locations:
            for loc in custom_locations:
                features.append({
                    "type": "Feature",
                    "properties": {
                        "name": loc.get('name', 'Custom Location'),
                        "description": loc.get('description', ''),
                        "website": loc.get('website', ''),
                        "tags": loc.get('tags', []),
                        "photo_url": loc.get('photo_url', ''),
                        "kind": "custom"
                    },
                    "geometry": {"type": "Point", "coordinates": [loc['lon'], loc['lat']]}
                })
        # Add LEAP locations if they exist
        if hasattr(self, 'leap_locations') and self.leap_locations:
            for loc in self.leap_locations:
                features.append({
                    "type": "Feature",
                    "properties": {
                        "name": loc.get('name', 'LEAP Location'),
                        "description": loc.get('description', ''),
                        "website": loc.get('website', ''),
                        "address": loc.get('address', ''),
                        "tags": loc.get('tags', ['LEAP', 'organization']),
                        "photo_url": loc.get('photo_url', ''),
                        "kind": "leap"
                    },
                    "geometry": {"type": "Point", "coordinates": [loc['lon'], loc['lat']]}
                })
        return {"type": "FeatureCollection", "features": features}

    def save_maplibre_map(self, filename: str = 'pittsburgh_maplibre.html', custom_locations: List[Dict] = None, boundary_geojson_path: Optional[str] = None, leap_locations: List[Dict] = None):
        """Export a standalone MapLibre GL JS + OSM raster HTML with clustering and popups."""
        # Load LEAP locations if not provided
        if leap_locations is None:
            leap_locations = self.load_leap_locations_from_csv()
        geojson = self._build_geojson(custom_locations)
        data_js = json.dumps(geojson)
        boundary_js = 'null'
        if boundary_geojson_path and os.path.exists(boundary_geojson_path):
            try:
                with open(boundary_geojson_path, 'r') as bf:
                    boundary_js = json.dumps(json.load(bf))
            except Exception:
                pass

        html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Pittsburgh Map (MapLibre + OSM)</title>
  <link href=\"https://cdn.jsdelivr.net/npm/maplibre-gl@3.6.1/dist/maplibre-gl.css\" rel=\"stylesheet\" />
  <script src=\"https://cdn.jsdelivr.net/npm/maplibre-gl@3.6.1/dist/maplibre-gl.js\"></script>
  <style>
    html, body {{ height: 100%; margin: 0; }}
    #map {{ position: absolute; inset: 0; }}
    .maplibregl-popup-content {{ font: 14px/1.4 -apple-system, system-ui, Segoe UI, Roboto, sans-serif; }}
    .popup-title {{ font-weight: 700; margin-bottom: 6px; color: #1f2937; }}
    .popup-tags {{ color: #6b7280; font-size: 12px; margin: 6px 0; }}
    .popup-img {{ width: 100%; height: 140px; object-fit: cover; border-radius: 6px; margin: 6px 0; }}
    .popup-link {{ display:inline-block; padding:6px 10px; background:#2563eb; color:#fff; text-decoration:none; border-radius:6px; }}
  </style>
  <script>
    const GEOJSON_DATA = {data_js};
    const BOUNDARY_DATA = {boundary_js};
  </script>
  </head>
<body>
  <div id=\"map\"></div>
  <script>
    // OSM raster style
    const style = {{
      version: 8,
      sources: {{
        osm: {{
          type: 'raster',
          tiles: ['https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png'],
          tileSize: 256,
          attribution: '© OpenStreetMap contributors'
        }}
      }},
      layers: [
        {{ id: 'osm', type: 'raster', source: 'osm' }}
      ]
    }};

    const map = new maplibregl.Map({{
      container: 'map',
      style,
      center: [{self.center_lon}, {self.center_lat}],
      zoom: 12
    }});

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    map.addControl(new maplibregl.FullscreenControl(), 'top-right');
    map.addControl(new maplibregl.ScaleControl({{ maxWidth: 140, unit: 'metric' }}));

    map.on('load', () => {{
      if (BOUNDARY_DATA) {{
        map.addSource('boundary', {{ type: 'geojson', data: BOUNDARY_DATA }});
        map.addLayer({{ id: 'boundary-line', type: 'line', source: 'boundary', paint: {{ 'line-color': '#2c7fb8', 'line-width': 2 }} }});
        map.addLayer({{ id: 'boundary-fill', type: 'fill', source: 'boundary', paint: {{ 'fill-color': '#7fcdbb', 'fill-opacity': 0.08 }} }});
      }}
      // Clustered GeoJSON source
      map.addSource('points', {{
        type: 'geojson',
        data: GEOJSON_DATA,
        cluster: true,
        clusterMaxZoom: 14,
        clusterRadius: 60
      }});

      // Cluster circles
      map.addLayer({{
        id: 'clusters',
        type: 'circle',
        source: 'points',
        filter: ['has', 'point_count'],
        paint: {{
          'circle-color': [
            'step', ['get', 'point_count'],
            '#93c5fd', 20, '#60a5fa', 100, '#3b82f6'
          ],
          'circle-radius': [
            'step', ['get', 'point_count'],
            15, 20, 22, 100, 30
          ]
        }}
      }});

      // Cluster labels
      map.addLayer({{
        id: 'cluster-count',
        type: 'symbol',
        source: 'points',
        filter: ['has', 'point_count'],
        layout: {{
          'text-field': ['to-string', ['get', 'point_count']],
          'text-size': 12
        }},
        paint: {{ 'text-color': '#111827' }}
      }});

      // Unclustered points
      map.addLayer({{
        id: 'unclustered-point',
        type: 'circle',
        source: 'points',
        filter: ['!', ['has', 'point_count']],
        paint: {{
          'circle-color': [
            'case',
            ['==', ['get', 'kind'], 'landmark'], '#ef4444',
            ['==', ['get', 'kind'], 'leap'], '#10b981',
            '#10b981'
          ],
          'circle-radius': 8,
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff'
        }}
      }});

      // Popup for unclustered points
      map.on('click', 'unclustered-point', (e) => {{
        const p = e.features[0].properties;
        const coords = e.features[0].geometry.coordinates.slice();
        const tags = (() => {{ try {{ return JSON.parse(p.tags); }} catch {{ return p.tags; }} }})();
        const img = p.photo_url ? `<img class="popup-img" src="${{p.photo_url}}" onerror="this.style.display='none'"/>` : '';
        const link = p.website ? `<div style="margin-top:6px;"><a class="popup-link" href="${{p.website}}" target="_blank">Visit Website</a></div>` : '';
        const tagsHtml = tags ? `<div class="popup-tags">${{Array.isArray(tags) ? tags.join(', ') : tags}}</div>` : '';
        const addressHtml = p.address ? `<div style="font-size:12px; color:#666; margin-top:4px;"><strong>Address:</strong> ${{p.address}}</div>` : '';
        new maplibregl.Popup()
          .setLngLat(coords)
          .setHTML(`
            <div class="popup-title">${{p.name}}</div>
            ${{addressHtml}}
            <div>${{p.description || ''}}</div>
            ${{tagsHtml}}
            ${{img}}
            ${{link}}
          `)
          .addTo(map);
      }});

      // Zoom into clusters on click
      map.on('click', 'clusters', (e) => {{
        const features = map.queryRenderedFeatures(e.point, {{ layers: ['clusters'] }});
        const clusterId = features[0].properties.cluster_id;
        map.getSource('points').getClusterExpansionZoom(clusterId, (err, zoom) => {{
          if (err) return;
          map.easeTo({{ center: features[0].geometry.coordinates, zoom }});
        }});
      }});

      map.on('mouseenter', 'clusters', () => {{ map.getCanvas().style.cursor = 'pointer'; }});
      map.on('mouseleave', 'clusters', () => {{ map.getCanvas().style.cursor = ''; }});
      map.on('mouseenter', 'unclustered-point', () => {{ map.getCanvas().style.cursor = 'pointer'; }});
      map.on('mouseleave', 'unclustered-point', () => {{ map.getCanvas().style.cursor = ''; }});
    }});
  </script>
</body>
</html>
"""

        with open(filename, 'w') as f:
            f.write(html)
        return filename

    def open_map_in_browser(self, filename: str = 'pittsburgh_interactive_map.html'):
        """Open the map in the default web browser."""
        if os.path.exists(filename):
            # Force open in browser with absolute path
            file_url = f'file://{os.path.abspath(filename)}'
            webbrowser.open(file_url)

    def serve_map_locally(self, filename: str = 'pittsburgh_interactive_map.html', 
                         port: int = 8000, open_browser: bool = True):
        """Serve the map HTML file via a local web server.
        
        Args:
            filename: Name of the HTML file to serve
            port: Port number for the local server (default: 8000)
            open_browser: If True, automatically open browser to localhost URL
            
        Returns:
            Server URL string if successful, None otherwise
        """
        if not os.path.exists(filename):
            return None
        
        # Change to directory containing the HTML file to serve relative paths correctly
        file_dir = os.path.dirname(os.path.abspath(filename)) or os.getcwd()
        file_name = os.path.basename(filename)
        
        class MapHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=file_dir, **kwargs)
            
            def log_message(self, format, *args):
                pass
        
        try:
            # Start server in a separate thread
            with socketserver.TCPServer(("", port), MapHandler) as httpd:
                server_url = f"http://localhost:{port}/{file_name}"
                
                # Print the URL
                print(f"\n{'='*60}")
                print(f"🗺️  Map is available at:")
                print(f"   {server_url}")
                print(f"{'='*60}\n")
                
                # Open browser automatically if requested
                if open_browser:
                    time.sleep(0.5)  # Give server a moment to start
                    webbrowser.open(server_url)
                
                # Serve forever (blocking call)
                httpd.serve_forever()
                
        except OSError:
            return None
        except KeyboardInterrupt:
            return None

    def pre_cache_images(self, custom_locations: List[Dict] = None):
        """Pre-download and cache all images before creating the map."""
        all_urls = []
        # Skip hardcoded landmarks - using only Google Sheets locations
        # for lm in self.landmarks:
        #     if lm.get('photo_url'):
        #         all_urls.append(lm['photo_url'])
        if custom_locations:
            for loc in custom_locations:
                if loc.get('photo_url'):
                    all_urls.append(loc['photo_url'])
        # Include LEAP location images
        if hasattr(self, 'leap_locations') and self.leap_locations:
            for loc in self.leap_locations:
                if loc.get('photo_url'):
                    all_urls.append(loc['photo_url'])
        
        for url in all_urls:
            self._get_image_src(url)

    def create_complete_map(self, custom_locations: List[Dict] = None, use_osm_boundary: bool = False, 
                           shapefile_path: Optional[str] = None,
                           google_sheet_id: Optional[str] = None,
                           google_sheet_names: Optional[List[str]] = None,
                           use_public_export: bool = True,
                           google_credentials_path: Optional[str] = None):
        """Create a complete interactive map with all features.
        
        Args:
            custom_locations: Optional list of custom location dictionaries
            use_osm_boundary: If True, fetch boundary from OSM Overpass API instead of using approximate coordinates
            shapefile_path: Path to shapefile (.shp) to use for boundary. Takes precedence over other options.
            google_sheet_id: Optional Google Sheets ID to load locations from (instead of CSV)
            google_sheet_names: Optional list of sheet names to load from. If None and google_sheet_id is provided, loads from all sheets.
            use_public_export: If True, uses public CSV export (no auth needed). If False, uses gspread (requires credentials).
            google_credentials_path: Path to Google service account JSON credentials file (required if use_public_export=False)
        """
        # Pre-cache all images first (including LEAP location images)
        # Load LEAP locations first to include them in image caching
        # Only load if not already loaded
        if not hasattr(self, 'leap_locations') or not self.leap_locations:
            if google_sheet_id:
                self.load_leap_locations_from_google_sheets(
                    google_sheet_id, 
                    google_sheet_names, 
                    use_public_export, 
                    google_credentials_path,
                    skip_duplicates=False  # No CSV to skip duplicates from
                )
            else:
                # Only load from CSV if no Google Sheet is provided
                self.load_leap_locations_from_csv()
        self.pre_cache_images(custom_locations)
        
        # Create base map (OSM is the default)
        self.create_base_map()
        
        # Add city boundary - shapefile takes priority, then OSM, then approximate
        if shapefile_path:
            if not self.add_boundary_from_shapefile(shapefile_path):
                if use_osm_boundary and not self.fetch_boundary_from_osm():
                    self.add_pittsburgh_boundary()
                elif not use_osm_boundary:
                    self.add_pittsburgh_boundary()
        elif use_osm_boundary:
            if not self.fetch_boundary_from_osm():
                self.add_pittsburgh_boundary()
        else:
            self.add_pittsburgh_boundary()
        
        # LEAP locations should already be loaded above (or were loaded before calling this method)
        # No need to reload them here
        
        # Add known landmarks (DISABLED - using only Google Sheets locations)
        # self.add_landmarks()
        
        # Add custom locations if provided
        if custom_locations:
            self.add_custom_locations(custom_locations)
        
        # Add LEAP locations (same pattern as landmarks - uses self.leap_locations)
        self.add_leap_locations()
        
        # Add interactive features
        self.add_marker_clustering()
        self.add_heatmap()
        self.add_minimap()
        self.add_geolocation()
        self.add_measurement_tools()
        self.add_fullscreen_button()
        self.add_draw_tools()
        self.add_mouse_position()
        self.add_layer_control()
        
        # Add search and filter (must be last to access all markers)
        self.add_search_and_filter()
        
        return self.map


def main():
    """Main function to demonstrate the Pittsburgh map functionality."""
    # Initialize the map
    pittsburgh_map = PittsburghMap()
    
    # Google Sheet ID from the provided URL
    # URL: https://docs.google.com/spreadsheets/d/1wZ_PzYdCR5bvpCKZ_AHT0P-Iln2mRGVlwMBNSyfuepM/edit
    google_sheet_id = "1wZ_PzYdCR5bvpCKZ_AHT0P-Iln2mRGVlwMBNSyfuepM"
    
    # Create the complete map with shapefile boundary
    # Priority: shapefile > OSM > approximate boundary
    shapefile_path = 'Pittsburgh_city_boundary/Pittsburgh_boundaries.shp'
    
    # Load locations ONLY from Google Sheets (disregarding CSV)
    # Load from specific sheets: Jaymar's list (blue), LEAP's list (green), Neighborhood Landmarks (red)
    
    # OPTION 1: Public Sheet (Recommended - Easiest)
    # Make sure your Google Sheet is shared publicly:
    # 1. Open the sheet and click "Share"
    # 2. Change to "Anyone with the link" → "Viewer"
    # 3. Click "Done"
    pittsburgh_map.load_leap_locations_from_google_sheets(
        sheet_id=google_sheet_id,
        sheet_names=["Jaymar's list", "LEAP's list", "Neighborhood Landmarks"],  # Load from specific sheets (exact names)
        use_public_export=True,  # Use public export (no auth needed)
        skip_duplicates=False  # No need to skip duplicates since we're not loading from CSV
    )
    
    # OPTION 2: Private Sheet with Authentication
    # If you prefer to keep the sheet private, uncomment the following:
    # pittsburgh_map.load_leap_locations_from_google_sheets(
    #     sheet_id=google_sheet_id,
    #     sheet_names=["Jaymar's list", "LEAP's list", "Neighborhood Landmarks"],
    #     use_public_export=False,  # Use authentication
    #     credentials_path="google_credentials.json",  # Path to your service account JSON
    #     skip_duplicates=False
    # )
    
    # Create the complete map (pass Google Sheet ID to ensure it loads from sheets, not CSV)
    pittsburgh_map.create_complete_map(
        custom_locations=None, 
        shapefile_path=shapefile_path if os.path.exists(shapefile_path) else None,
        use_osm_boundary=False,
        google_sheet_id=google_sheet_id,  # Ensure it uses Google Sheets instead of CSV
        google_sheet_names=["Jaymar's list", "LEAP's list", "Neighborhood Landmarks"],  # Exact sheet names
        use_public_export=True
    )
    
    # Print summary of loaded locations
    total_locations = len(pittsburgh_map.leap_locations) if hasattr(pittsburgh_map, 'leap_locations') else 0
    print(f"\n{'='*60}")
    print(f"📊 Summary:")
    print(f"   Total locations loaded: {total_locations}")
    print(f"{'='*60}\n")
    
    # Save the map
    filename = pittsburgh_map.save_map()
    if filename:
        # Serve via local web server
        try:
            pittsburgh_map.serve_map_locally(filename, port=8000, open_browser=True)
        except KeyboardInterrupt:
            print("\n\nServer stopped.")
            pass


if __name__ == "__main__":
    main()
    
    # Example: Load from Google Sheets instead of CSV
    # Uncomment and modify the following to use Google Sheets:
    #
    # pittsburgh_map = PittsburghMap()
    # 
    # # Method 1: Public export (sheet must be public)
    # # Get sheet ID from URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit
    # sheet_id = "YOUR_SHEET_ID_HERE"
    # sheet_names = ["Sheet1", "Sheet2", "Sheet3"]  # List of sheet names to load
    # 
    # pittsburgh_map.create_complete_map(
    #     custom_locations=None,
    #     shapefile_path=shapefile_path if os.path.exists(shapefile_path) else None,
    #     use_osm_boundary=False,
    #     google_sheet_id=sheet_id,
    #     google_sheet_names=sheet_names,  # Load from multiple sheets
    #     use_public_export=True  # Use public CSV export (no auth needed)
    # )
    #
    # # Method 2: Using gspread (for private sheets, requires credentials)
    # # pittsburgh_map.create_complete_map(
    # #     custom_locations=None,
    # #     shapefile_path=shapefile_path if os.path.exists(shapefile_path) else None,
    # #     use_osm_boundary=False,
    # #     google_sheet_id=sheet_id,
    # #     google_sheet_names=sheet_names,
    # #     use_public_export=False,
    # #     google_credentials_path="path/to/credentials.json"
    # # )

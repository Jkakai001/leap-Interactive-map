# Interactive Pittsburgh Map Project

A comprehensive Python-based solution for creating interactive maps of Pittsburgh with city boundaries, landmarks, and custom locations. This project provides tools for mapping experts to visualize locations with detailed information, photos, and links.

## Features

- **Interactive Map**: Built with Folium for smooth, interactive web-based maps
- **Pittsburgh City Boundary**: Visual representation of city limits
- **Known Landmarks**: Pre-loaded with 8 major Pittsburgh landmarks including:
  - Point State Park
  - Carnegie Mellon University
  - University of Pittsburgh
  - PNC Park
  - Heinz Field
  - Andy Warhol Museum
  - Phipps Conservatory
  - Duquesne Incline
- **Clickable Locations**: Each location shows:
  - Detailed descriptions
  - High-quality photos
  - Website links
  - Tags for categorization
- **Custom Location Support**: Easy integration of your own coordinates
- **Advanced Features**:
  - Layer control for different map styles
  - Measurement tools for distance/area
  - Fullscreen mode
  - Marker clustering for performance
  - Heatmap visualization

## Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Setup

1. **Clone or download this project**:
   ```bash
   git clone <your-repo-url>
   cd LEAP
   ```

2. **Install required packages**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python -c "import folium; print('Folium installed successfully')"
   ```

## Quick Start

### Basic Usage

1. **Run the main script**:
   ```bash
   python pittsburgh_map.py
   ```

2. **The script will**:
   - Create an interactive map
   - Add Pittsburgh boundaries
   - Add known landmarks
   - Save as `pittsburgh_interactive_map.html`
   - Open in your default browser

### Adding Your Own Locations

```python
from pittsburgh_map import PittsburghMap

# Initialize the map
map_creator = PittsburghMap()

# Define your custom locations
custom_locations = [
    {
        'name': 'Your Location Name',
        'lat': 40.4500,  # Your latitude
        'lon': -79.9500,  # Your longitude
        'description': 'Description of your location',
        'website': 'https://your-website.com',
        'tags': ['tag1', 'tag2', 'tag3'],
        'photo_url': 'https://your-photo-url.com/image.jpg'
    }
]

# Create the complete map
map_creator.create_complete_map(custom_locations)

# Save and open
map_creator.save_map('my_pittsburgh_map.html')
map_creator.open_map_in_browser('my_pittsburgh_map.html')
```

## File Structure

```
LEAP/
├── pittsburgh_map.py          # Main interactive map script
├── advanced_pittsburgh_map.py # Advanced features and GeoJSON support
├── data_loader.py             # Utilities for loading location data
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Detailed Usage

### Main Script (`pittsburgh_map.py`)

The main script provides a complete `PittsburghMap` class with the following methods:

- `create_base_map()`: Creates the base interactive map
- `add_pittsburgh_boundary()`: Adds city boundary visualization
- `add_landmarks()`: Adds known Pittsburgh landmarks
- `add_custom_locations(locations)`: Adds your custom locations
- `save_map(filename)`: Saves map to HTML file
- `open_map_in_browser(filename)`: Opens map in browser

### Advanced Features (`advanced_pittsburgh_map.py`)

For more sophisticated mapping needs:

- **GeoJSON Support**: Load real Pittsburgh boundary data
- **Heatmap Visualization**: Show location density
- **Marker Clustering**: Better performance with many locations
- **Custom Styling**: Advanced map styling options

### Data Loading (`data_loader.py`)

Utilities for loading location data from various sources:

- **CSV Files**: Load locations from spreadsheet data
- **JSON Files**: Load from structured JSON data
- **APIs**: Connect to external data sources
- **Google Sheets**: Load from multiple sheets in a Google Spreadsheet
- **Database Integration**: Ready for database connections

## Data Sources and APIs

### Recommended Data Sources

1. **Pittsburgh City Data**:
   - [OpenDataPittsburgh](https://data.wprdc.org/)
   - [Allegheny County GIS](https://gisdata.alleghenycounty.us/)

2. **Landmark Data**:
   - [Wikipedia API](https://en.wikipedia.org/api/rest_v1/)
   - [OpenStreetMap Nominatim](https://nominatim.org/)

3. **Photo Sources**:
   - [Wikimedia Commons](https://commons.wikimedia.org/)
   - [Flickr API](https://www.flickr.com/services/api/)

### Example API Integration

```python
from data_loader import PittsburghDataLoader

loader = PittsburghDataLoader()

# Load from OpenStreetMap Nominatim API
locations = loader.load_from_api(
    'https://nominatim.openstreetmap.org/search',
    params={'q': 'Pittsburgh landmarks', 'format': 'json'}
)
```

## Customization

### Adding New Landmarks

Edit the `landmarks` list in `pittsburgh_map.py`:

```python
landmarks = [
    {
        'name': 'New Landmark',
        'lat': 40.4400,
        'lon': -79.9900,
        'description': 'Description here',
        'website': 'https://website.com',
        'tags': ['tag1', 'tag2'],
        'photo_url': 'https://photo-url.com'
    }
]
```

### Styling the Map

Customize map appearance:

```python
# Different tile layers
folium.TileLayer('CartoDB positron').add_to(map)
folium.TileLayer('CartoDB dark_matter').add_to(map)

# Custom marker icons
folium.Icon(color='red', icon='info-sign')
folium.Icon(color='green', icon='star')
```

### Boundary Data

For real Pittsburgh boundary data:

1. Download GeoJSON from [OpenDataPittsburgh](https://data.wprdc.org/)
2. Use the `advanced_pittsburgh_map.py` script
3. Provide the GeoJSON URL or file path

## Troubleshooting

### Common Issues

1. **Import Errors**:
   ```bash
   pip install --upgrade folium pandas requests
   ```

2. **Map Not Displaying**:
   - Check that the HTML file was created
   - Verify browser compatibility
   - Try opening the file directly

3. **Missing Photos**:
   - Verify photo URLs are accessible
   - Use placeholder images for testing
   - Check CORS policies for external images

### Performance Tips

- Use marker clustering for >100 locations
- Optimize image sizes for faster loading
- Consider using local image files instead of URLs
- Use heatmaps for density visualization

## Examples

### Example 1: Basic Map with Custom Locations

```python
from pittsburgh_map import PittsburghMap

# Your coordinates
locations = [
    {
        'name': 'Downtown Office',
        'lat': 40.4417,
        'lon': -79.9967,
        'description': 'Main office location',
        'website': 'https://company.com',
        'tags': ['office', 'downtown'],
        'photo_url': 'https://via.placeholder.com/400x300'
    }
]

map_creator = PittsburghMap()
map_creator.create_complete_map(locations)
map_creator.save_map('office_map.html')
```

### Example 2: Loading from CSV

```python
from data_loader import PittsburghDataLoader
from pittsburgh_map import PittsburghMap

# Load data
loader = PittsburghDataLoader()
loader.load_from_csv('my_locations.csv')

# Create map
map_creator = PittsburghMap()
map_creator.create_complete_map(loader.get_locations())
map_creator.save_map('csv_map.html')
```

### Example 3: Loading from Google Sheets (Multiple Sheets)

You can load locations from different sheets in a Google Spreadsheet. There are two methods:

#### Method 1: Public Export (No Authentication Required)

For public Google Sheets, you can use the public CSV export method:

```python
from pittsburgh_map import PittsburghMap
import os

# Initialize the map
map_creator = PittsburghMap()

# Get your Google Sheet ID from the URL:
# https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit
sheet_id = "YOUR_SHEET_ID_HERE"

# Specify which sheets to load from
sheet_names = ["Sheet1", "Sheet2", "Sheet3"]  # Load from multiple sheets

# Create map with Google Sheets data
shapefile_path = 'Pittsburgh_city_boundary/Pittsburgh_boundaries.shp'
map_creator.create_complete_map(
    custom_locations=None,
    shapefile_path=shapefile_path if os.path.exists(shapefile_path) else None,
    use_osm_boundary=False,
    google_sheet_id=sheet_id,
    google_sheet_names=sheet_names,  # Load from multiple sheets
    use_public_export=True  # Use public CSV export (no auth needed)
)

# Save and open
map_creator.save_map('google_sheets_map.html')
map_creator.open_map_in_browser('google_sheets_map.html')
```

#### Method 2: Using gspread (For Private Sheets)

For private Google Sheets, you'll need to set up authentication:

1. **Install gspread** (if not already installed):
   ```bash
   pip install gspread google-auth
   ```

2. **Set up Google Service Account**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Google Sheets API
   - Create a Service Account and download the JSON credentials file
   - Share your Google Sheet with the service account email

3. **Use the credentials**:
   ```python
   from pittsburgh_map import PittsburghMap
   import os

   map_creator = PittsburghMap()
   
   sheet_id = "YOUR_SHEET_ID_HERE"
   sheet_names = ["Sheet1", "Sheet2", "Sheet3"]
   credentials_path = "path/to/your/credentials.json"
   
   map_creator.create_complete_map(
       custom_locations=None,
       shapefile_path=shapefile_path if os.path.exists(shapefile_path) else None,
       use_osm_boundary=False,
       google_sheet_id=sheet_id,
       google_sheet_names=sheet_names,
       use_public_export=False,  # Use gspread authentication
       google_credentials_path=credentials_path
   )
   
   map_creator.save_map('private_sheets_map.html')
   ```

#### Google Sheets Format

Your Google Sheet should have the following columns (case-insensitive):
- `ORGANIZATION NAME` or `Name` - The location name
- `XY-COODRINATE` or `Coordinates` - Coordinates in format "lat, lon"
- `ADDRESS` or `Address` - Street address (optional)
- `BRIEF DESCRIPTION` or `Description` - Description text (optional)
- `WEBSITE` or `Website` - Website URL (optional)
- `PHOTO_URL` or `Photo URL` - Photo URL (optional)

**Note**: The coordinate format should be: `"40.4639, -79.8957"` (latitude, longitude separated by comma).

#### Loading from Multiple Sheets

You can load locations from multiple sheets in the same spreadsheet:

```python
# Load from specific sheets
sheet_names = ["LEAP Locations", "Community Centers", "Parks"]

# Or load from all sheets (when using gspread)
sheet_names = None  # Will load from all sheets automatically
```

## Contributing

To add new features or improve the project:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For questions or issues:

1. Check the troubleshooting section
2. Review the example code
3. Open an issue in the repository
4. Contact the development team

## Future Enhancements

- Real-time data integration
- Mobile-responsive design
- Database connectivity
- Advanced analytics
- Export to various formats
- Integration with GIS software

---

**Happy Mapping!** 🗺️

This project provides a solid foundation for creating interactive Pittsburgh maps. Customize it to fit your specific needs and data sources.

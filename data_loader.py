#!/usr/bin/env python3
"""
Data Loader for Pittsburgh Map
This script provides utilities to load and process location data
from various sources like CSV files, APIs, and databases.
"""

import pandas as pd
import json
import requests
from typing import List, Dict, Optional
import csv

# Try to import gspread for Google Sheets support
try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

class PittsburghDataLoader:
    def __init__(self):
        """Initialize the data loader."""
        self.locations = []
    
    def load_from_csv(self, csv_file: str) -> List[Dict]:
        """
        Load location data from a CSV file.
        Expected columns: name, lat, lon, description, website, tags, photo_url
        """
        try:
            df = pd.read_csv(csv_file)
            locations = df.to_dict('records')
            self.locations.extend(locations)
            print(f"Loaded {len(locations)} locations from {csv_file}")
            return locations
        except Exception as e:
            print(f"Error loading CSV file {csv_file}: {e}")
            return []
    
    def load_from_json(self, json_file: str) -> List[Dict]:
        """Load location data from a JSON file."""
        try:
            with open(json_file, 'r') as f:
                locations = json.load(f)
            self.locations.extend(locations)
            print(f"Loaded {len(locations)} locations from {json_file}")
            return locations
        except Exception as e:
            print(f"Error loading JSON file {json_file}: {e}")
            return []
    
    def load_from_api(self, api_url: str, api_key: str = None) -> List[Dict]:
        """
        Load location data from an API.
        This is a template - you'll need to adapt it for your specific API.
        """
        try:
            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            # Process the API response based on its structure
            locations = self._process_api_response(data)
            self.locations.extend(locations)
            print(f"Loaded {len(locations)} locations from API")
            return locations
        except Exception as e:
            print(f"Error loading from API {api_url}: {e}")
            return []
    
    def _process_api_response(self, data: Dict) -> List[Dict]:
        """
        Process API response data into the expected format.
        Override this method based on your API's response structure.
        """
        locations = []
        # Example processing - adapt based on your API
        if 'results' in data:
            for item in data['results']:
                location = {
                    'name': item.get('name', 'Unknown'),
                    'lat': float(item.get('latitude', 0)),
                    'lon': float(item.get('longitude', 0)),
                    'description': item.get('description', ''),
                    'website': item.get('website', ''),
                    'tags': item.get('tags', []),
                    'photo_url': item.get('photo_url', '')
                }
                locations.append(location)
        return locations
    
    def save_to_csv(self, filename: str):
        """Save current locations to a CSV file."""
        if self.locations:
            df = pd.DataFrame(self.locations)
            df.to_csv(filename, index=False)
            print(f"Saved {len(self.locations)} locations to {filename}")
        else:
            print("No locations to save")
    
    def save_to_json(self, filename: str):
        """Save current locations to a JSON file."""
        if self.locations:
            with open(filename, 'w') as f:
                json.dump(self.locations, f, indent=2)
            print(f"Saved {len(self.locations)} locations to {filename}")
        else:
            print("No locations to save")
    
    def get_locations(self) -> List[Dict]:
        """Get all loaded locations."""
        return self.locations
    
    def clear_locations(self):
        """Clear all loaded locations."""
        self.locations = []
        print("Cleared all locations")
    
    def load_from_google_sheets(self, sheet_id: str, sheet_names: List[str] = None,
                                use_public_export: bool = True,
                                credentials_path: Optional[str] = None) -> List[Dict]:
        """
        Load location data from Google Sheets (supports multiple sheets).
        
        Args:
            sheet_id: Google Sheets ID (from the URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit)
            sheet_names: List of sheet names to load from. If None, loads from all sheets.
            use_public_export: If True, uses public CSV export (no auth needed, sheet must be public).
                               If False, uses gspread (requires credentials).
            credentials_path: Path to Google service account JSON credentials file (required if use_public_export=False)
            
        Returns:
            List of location dictionaries
        """
        all_locations = []
        
        if use_public_export:
            # Method 1: Public CSV export (simpler, no authentication needed)
            try:
                if sheet_names is None:
                    sheet_names = ['Sheet1']  # Default to first sheet
                
                for sheet_name in sheet_names:
                    # URL format for public CSV export
                    encoded_sheet_name = sheet_name.replace(' ', '%20')
                    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}"
                    
                    try:
                        df = pd.read_csv(csv_url, quotechar='"', skipinitialspace=True, on_bad_lines='skip', encoding='utf-8')
                        locations = df.to_dict('records')
                        all_locations.extend(locations)
                        print(f"Loaded {len(locations)} locations from sheet '{sheet_name}'")
                    except Exception as e:
                        print(f"Warning: Could not load sheet '{sheet_name}': {e}")
                        # Try alternative URL format
                        try:
                            csv_url_alt = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid=0"
                            df = pd.read_csv(csv_url_alt, quotechar='"', skipinitialspace=True, on_bad_lines='skip', encoding='utf-8')
                            locations = df.to_dict('records')
                            all_locations.extend(locations)
                            print(f"Loaded {len(locations)} locations from sheet using alternative method")
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
                        
                        locations = df.to_dict('records')
                        all_locations.extend(locations)
                        print(f"Loaded {len(locations)} locations from sheet '{sheet_name}'")
                    except Exception as e:
                        print(f"Warning: Could not load sheet '{sheet_name}': {e}")
                        
            except Exception as e:
                print(f"Error loading from Google Sheets (gspread): {e}")
                return all_locations
        
        self.locations.extend(all_locations)
        return all_locations

def main():
    """Example usage of the data loader."""
    loader = PittsburghDataLoader()
    
    # Example: Load from CSV
    # loader.load_from_csv('pittsburgh_locations.csv')
    
    # Example: Load from JSON
    # loader.load_from_json('pittsburgh_locations.json')
    
    # Example: Load from API
    # loader.load_from_api('https://api.example.com/locations', 'your_api_key')
    
    # Get all locations
    locations = loader.get_locations()
    print(f"Total locations loaded: {len(locations)}")

if __name__ == "__main__":
    main()

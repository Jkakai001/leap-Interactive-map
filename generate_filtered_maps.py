#!/usr/bin/env python3
"""
Generate two filtered interactive maps:
1. LEAP locations + landmarks only
2. Jaymars list + landmarks only
"""

import json
import re
import os
import http.server
import socketserver
import webbrowser
import time
from typing import List, Dict

def extract_locations_data(html_content: str) -> List[Dict]:
    """Extract LOCATIONS_DATA from HTML file."""
    # Find the LOCATIONS_DATA line
    pattern = r'const LOCATIONS_DATA = (\[.*?\]);'
    match = re.search(pattern, html_content, re.DOTALL)
    
    if not match:
        raise ValueError("Could not find LOCATIONS_DATA in HTML file")
    
    locations_json = match.group(1)
    locations = json.loads(locations_json)
    return locations

def filter_locations(locations: List[Dict], include_tags: List[str], deduplicate: bool = True) -> List[Dict]:
    """Filter locations to only include those with any of the specified tags.
    When deduplicate is True, keeps one entry per (name, lat, lon), preferring the entry
    whose tags match this map's primary list (leaps_list vs jaymars_list).
    """
    filtered = []
    for loc in locations:
        tags = [tag.lower() for tag in loc.get('tags', [])]
        if any(tag.lower() in tags for tag in include_tags):
            filtered.append(loc)
    if not deduplicate:
        return filtered
    # Deduplicate by (name, lat, lon): keep first occurrence (source order = LEAP then Jaymar then Landmarks)
    seen = {}
    for loc in filtered:
        key = (loc.get('name', '').lower(), round(loc['lat'], 6), round(loc.get('lon', loc.get('lng', 0)), 6))
        if key not in seen:
            seen[key] = loc
    return list(seen.values())

def strip_marker_blocks_by_tags(html_content: str, include_tags: List[str]) -> str:
    """Remove from HTML every marker block whose popup does NOT contain any of include_tags.
    Only strips the feature_group marker section (before feature_group.addTo(map)); preserves
    feature_group.addTo(map), polygon, marker_cluster, and layer control so the map still renders.
    """
    # Find where the LEAP/markers feature_group is added to the map (the one that has our markers).
    # There are 3 feature_groups in the file; we need the one at line ~3471 (feature_group_ca9dce...).
    add_to_match = re.search(
        r'\n\s+feature_group_ca9dce572abbf289b181d8525062f438\.addTo\(map_\w+\)',
        html_content
    )
    if not add_to_match:
        return html_content
    boundary = add_to_match.start()
    content_to_strip = html_content[:boundary]
    content_after = html_content[boundary:]

    # Split only the first section on start of each marker block (keep delimiter so we can reassemble)
    marker_start = re.compile(r'(\s*var marker_\w+ = L\.marker\()', re.DOTALL)
    parts = marker_start.split(content_to_strip)
    if len(parts) <= 1:
        return html_content
    result = [parts[0]]
    i = 1
    while i + 1 < len(parts):
        delim, body = parts[i], parts[i + 1]
        block = delim + body
        if any(tag in block for tag in include_tags):
            result.append(block)
        i += 2
    if i < len(parts):
        result.append(parts[i])
    content_after = ''.join(result) + content_after

    # Remove the marker_cluster section entirely so both maps don't show the same 56 markers.
    # The cluster has all markers; without it, only the feature_group (filtered above) is visible.
    content_after = _remove_marker_cluster_section(content_after)
    return content_after


def _remove_marker_cluster_section(html_content: str) -> str:
    """Remove the marker_cluster block and its 'Clustered Locations' overlay so filtered maps
    show only the feature_group markers (LEAP vs Jaymars), not the full cluster.
    """
    # Remove from "var marker_cluster_XXX = L.markerClusterGroup(" through just before "var heat_map_"
    cluster_start = re.search(
        r'\n\s+var marker_cluster_\w+ = L\.markerClusterGroup\(',
        html_content
    )
    heat_start = re.search(
        r'\n\s+var heat_map_\w+ = L\.heatLayer\(',
        html_content
    )
    if cluster_start and heat_start and cluster_start.start() < heat_start.start():
        html_content = (
            html_content[:cluster_start.start()] +
            html_content[heat_start.start():]
        )
    # Remove "Clustered Locations" : marker_cluster_xxx from the layer control overlays (avoids undefined ref)
    html_content = re.sub(
        r'\n\s+"Clustered Locations"\s*:\s*marker_cluster_\w+,?\s*',
        '\n                    ',
        html_content,
        count=1
    )
    return html_content


def replace_locations_data(html_content: str, filtered_locations: List[Dict]) -> str:
    """Replace LOCATIONS_DATA in HTML with filtered data."""
    locations_json = json.dumps(filtered_locations, separators=(',', ':'))
    # Find the LOCATIONS_DATA line and replace it
    pattern = r'const LOCATIONS_DATA = \[.*?\];'
    # Use re.escape on the replacement to handle special characters
    replacement = f'const LOCATIONS_DATA = {re.escape(locations_json)};'
    # Actually, we don't want to escape - we want the literal JSON. Let's use a different approach
    # Find the exact match and replace
    match = re.search(pattern, html_content, re.DOTALL)
    if match:
        start, end = match.span()
        html_content = html_content[:start] + f'const LOCATIONS_DATA = {locations_json};' + html_content[end:]
    return html_content

def add_auto_filter_code(html_content: str, include_tags: List[str], filtered_locations: List[Dict]) -> str:
    """Add JavaScript code to automatically apply filters and remove non-matching markers on page load."""
    # Create JavaScript code to auto-apply filters and remove markers
    auto_filters_json = json.dumps([tag.lower() for tag in include_tags])
    # Create a list of filtered location coordinates for matching
    filtered_coords_list = []
    for loc in filtered_locations:
        lat = loc['lat']
        lon = loc.get('lon', loc.get('lng', 0))
        filtered_coords_list.append(f"{lat:.6f},{lon:.6f}")
    
    filtered_coords_json = json.dumps(filtered_coords_list)
    filtered_names_json = json.dumps([loc['name'].lower() for loc in filtered_locations])
    
    filter_code = f"""
            // Auto-apply filters on page load and remove non-matching markers
            (function() {{
                const autoFilters = {auto_filters_json};
                const filteredLocationNames = {filtered_names_json};
                const filteredCoords = {filtered_coords_json};
                
                function hideNonMatchingMarkers() {{
                    // Find the map object - iterate through all L.map instances
                    let map = null;
                    if (typeof L !== 'undefined' && L.map && L.map._instances) {{
                        // Get the first (and usually only) map instance
                        for (let id in L.map._instances) {{
                            map = L.map._instances[id];
                            break;
                        }}
                    }}
                    
                    // Fallback: try to find map by looking for leaflet-container
                    if (!map && typeof L !== 'undefined') {{
                        const container = document.querySelector('.leaflet-container');
                        if (container && container._leaflet_id) {{
                            map = L.map._instances[container._leaflet_id];
                        }}
                    }}
                    
                    if (!map) {{
                        setTimeout(hideNonMatchingMarkers, 500);
                        return;
                    }}
                    
                    // Match by Tags in popup so LEAP map keeps only leaps_list/landmarks,
                    // Jaymars map keeps only jaymars_list/landmarks (avoids duplicate markers)
                    function markerMatches(marker) {{
                        try {{
                            const popup = marker.getPopup();
                            if (popup) {{
                                const popupContent = popup.getContent();
                                if (popupContent) {{
                                    const content = typeof popupContent === 'string' ? popupContent : (popupContent.textContent || popupContent.innerHTML || '');
                                    // Extract Tags line (e.g. "Tags: LEAP, organization, leaps_list")
                                    const tagsMatch = content.match(/<strong>Tags:<\/strong>\\s*([^<]+)/i);
                                    if (tagsMatch) {{
                                        const tagsStr = tagsMatch[1].toLowerCase();
                                        // Keep marker only if its popup Tags contain one of our include_tags
                                        for (let i = 0; i < autoFilters.length; i++) {{
                                            if (tagsStr.indexOf(autoFilters[i]) !== -1) {{
                                                return true;
                                            }}
                                        }}
                                        return false;
                                    }}
                                    // Fallback: check Source line (e.g. "Source: LEAP's list")
                                    const sourceMatch = content.match(/<strong>Source:<\/strong>\\s*([^<]+)/i);
                                    if (sourceMatch) {{
                                        const source = sourceMatch[1].toLowerCase().replace(/'/g, '').replace(/\\s+/g, '_');
                                        for (let i = 0; i < autoFilters.length; i++) {{
                                            if (source.indexOf(autoFilters[i]) !== -1) {{
                                                return true;
                                            }}
                                        }}
                                    }}
                                }}
                            }}
                        }} catch(e) {{
                            // Ignore popup errors
                        }}
                        // Fallback: match by coordinates (for markers without Tags in popup)
                        const latlng = marker.getLatLng();
                        if (latlng) {{
                            const tolerance = 0.0002;
                            for (let coord of filteredCoords) {{
                                const [lat, lng] = coord.split(',').map(parseFloat);
                                if (Math.abs(lat - latlng.lat) < tolerance && Math.abs(lng - latlng.lng) < tolerance) {{
                                    return true;
                                }}
                            }}
                        }}
                        return false;
                    }}
                    
                    // Collect ALL markers from the map - be very thorough
                    let allMarkers = [];
                    
                    function collectMarkers(layer, parentLayer) {{
                        if (layer instanceof L.Marker) {{
                            allMarkers.push({{marker: layer, parent: parentLayer}});
                        }} else if (layer instanceof L.MarkerClusterGroup) {{
                            // Handle marker clusters - get all markers from the cluster
                            if (layer._markerClusters) {{
                                Object.values(layer._markerClusters).forEach(function(cluster) {{
                                    if (cluster._markers) {{
                                        cluster._markers.forEach(function(marker) {{
                                            allMarkers.push({{marker: marker, parent: layer}});
                                        }});
                                    }}
                                }});
                            }}
                            layer.eachLayer(function(sublayer) {{
                                if (sublayer instanceof L.Marker) {{
                                    allMarkers.push({{marker: sublayer, parent: layer}});
                                }}
                            }});
                        }} else if (layer instanceof L.LayerGroup || layer instanceof L.FeatureGroup) {{
                            // Recursively collect from nested groups
                            if (layer._layers) {{
                                Object.values(layer._layers).forEach(function(sublayer) {{
                                    collectMarkers(sublayer, layer);
                                }});
                            }}
                            layer.eachLayer(function(sublayer) {{
                                collectMarkers(sublayer, layer);
                            }});
                        }}
                    }}
                    
                    // Collect from all layers on the map
                    map.eachLayer(function(layer) {{
                        collectMarkers(layer, null);
                    }});
                    
                    // Also check map._layers directly
                    if (map._layers) {{
                        Object.values(map._layers).forEach(function(layer) {{
                            collectMarkers(layer, null);
                        }});
                    }}
                    
                    // Remove non-matching markers - be more aggressive
                    let keptCount = 0;
                    let removedCount = 0;
                    const markersToKeep = new Set();
                    
                    // First pass: identify markers to keep
                    allMarkers.forEach(function(item) {{
                        const matches = markerMatches(item.marker);
                        if (matches) {{
                            markersToKeep.add(item.marker._leaflet_id || item.marker);
                            keptCount++;
                        }}
                    }});
                    
                    // Second pass: remove all non-matching markers
                    allMarkers.forEach(function(item) {{
                        const shouldKeep = markersToKeep.has(item.marker._leaflet_id || item.marker);
                        if (!shouldKeep) {{
                            // Remove the marker from the map/layer
                            try {{
                                // Try multiple removal methods
                                if (item.parent) {{
                                    if (item.parent.removeLayer) {{
                                        item.parent.removeLayer(item.marker);
                                    }}
                                    if (item.parent.hasLayer && item.parent.hasLayer(item.marker)) {{
                                        item.parent.removeLayer(item.marker);
                                    }}
                                }}
                                if (map.hasLayer && map.hasLayer(item.marker)) {{
                                    map.removeLayer(item.marker);
                                }}
                                // Also try removing by ID
                                if (item.marker._leaflet_id && map._layers) {{
                                    delete map._layers[item.marker._leaflet_id];
                                }}
                                removedCount++;
                            }} catch(e) {{
                                console.warn('Error removing marker:', e);
                            }}
                        }}
                    }});
                    
                    // Third pass: clean up empty layer groups
                    map.eachLayer(function(layer) {{
                        if ((layer instanceof L.LayerGroup || layer instanceof L.FeatureGroup) && layer.getLayers) {{
                            const layers = layer.getLayers();
                            if (layers.length === 0) {{
                                try {{
                                    map.removeLayer(layer);
                                }} catch(e) {{
                                    // Ignore errors
                                }}
                            }}
                        }}
                    }});
                    
                    console.log(`Marker filtering complete:`);
                    console.log(`  Total markers found: ${{allMarkers.length}}`);
                    console.log(`  Markers kept: ${{keptCount}}`);
                    console.log(`  Markers removed: ${{removedCount}}`);
                    console.log(`  Expected to keep: ${{filteredCoords.length}} locations`);
                }}
                
                function applyAutoFilters() {{
                    if (typeof activeFilters === 'undefined') {{
                        setTimeout(applyAutoFilters, 500);
                        return;
                    }}
                    
                    // Clear existing filters
                    activeFilters.clear();
                    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
                    
                    // Add auto filters
                    autoFilters.forEach(tag => {{
                        activeFilters.add(tag);
                        let btn = document.querySelector(`[data-tag="${{tag}}"]`);
                        if (btn) {{
                            btn.classList.add('active');
                        }}
                    }});
                    
                    // Hide non-matching markers first
                    hideNonMatchingMarkers();
                    
                    // Apply the filters
                    if (typeof performSearch === 'function') {{
                        setTimeout(function() {{
                            performSearch();
                        }}, 1000);
                    }}
                }}
                
                // Wait for page to load and run filtering multiple times
                // Run more aggressively to catch all markers
                let runCount = 0;
                function runFiltering() {{
                    runCount++;
                    applyAutoFilters();
                    if (runCount < 10) {{
                        setTimeout(runFiltering, 500);
                    }}
                }}
                
                window.addEventListener('load', function() {{
                    setTimeout(runFiltering, 500);
                }});
                setTimeout(runFiltering, 1000);
            }})();
"""
    
    # Insert the code after LOCATIONS_DATA definition
    # Find the line with "let activeFilters" after LOCATIONS_DATA
    pattern = r'(let activeFilters = new Set\(\);)'
    match = re.search(pattern, html_content)
    if match:
        insert_pos = match.end()
        html_content = html_content[:insert_pos] + filter_code + html_content[insert_pos:]
    
    return html_content

def generate_filtered_map(input_file: str, output_file: str, include_tags: List[str], title_suffix: str):
    """Generate a filtered map HTML file."""
    print(f"Reading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    print(f"Extracting locations data...")
    locations = extract_locations_data(html_content)
    print(f"Found {len(locations)} total locations")
    
    print(f"Filtering locations with tags: {include_tags}...")
    filtered_locations = filter_locations(locations, include_tags)
    print(f"Filtered to {len(filtered_locations)} locations")
    
    print(f"Stripping non-matching marker blocks from HTML...")
    html_content = strip_marker_blocks_by_tags(html_content, include_tags)
    
    print(f"Updating HTML with filtered data...")
    html_content = replace_locations_data(html_content, filtered_locations)
    
    print(f"Adding auto-filter code...")
    html_content = add_auto_filter_code(html_content, include_tags, filtered_locations)
    
    # Update title if there's one
    if '<title>' in html_content:
        html_content = re.sub(
            r'<title>.*?</title>',
            f'<title>Pittsburgh Map - {title_suffix}</title>',
            html_content
        )
    else:
        # Add title in head
        html_content = html_content.replace(
            '</head>',
            f'<title>Pittsburgh Map - {title_suffix}</title>\n</head>'
        )
    
    # Update the panel title
    html_content = html_content.replace(
        '🔍 Find Places',
        f'🔍 Find Places - {title_suffix}'
    )
    
    print(f"Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✓ Created {output_file} with {len(filtered_locations)} locations\n")

if __name__ == '__main__':
    input_file = 'pittsburgh_interactive_map.html'
    
    # Generate LEAP + Landmarks map
    generate_filtered_map(
        input_file=input_file,
        output_file='pittsburgh_map_leap_landmarks.html',
        include_tags=['leaps_list', 'neighborhood_landmarks'],
        title_suffix='LEAP & Landmarks'
    )
    
    # Generate Jaymars + Landmarks map
    generate_filtered_map(
        input_file=input_file,
        output_file='pittsburgh_map_jaymars_landmarks.html',
        include_tags=['jaymars_list', 'neighborhood_landmarks'],
        title_suffix='Jaymars List & Landmarks'
    )
    
    print("Done! Created two filtered map files:")
    print("  - pittsburgh_map_leap_landmarks.html")
    print("  - pittsburgh_map_jaymars_landmarks.html")
    
    # Start local server and show both links
    port = 8000
    file_dir = os.path.dirname(os.path.abspath('pittsburgh_map_leap_landmarks.html')) or os.getcwd()
    
    class MapHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=file_dir, **kwargs)
        
        def log_message(self, format, *args):
            pass
    
    try:
        with socketserver.TCPServer(("", port), MapHandler) as httpd:
            print(f"\n{'='*60}")
            print(f"🗺️  Maps are available at:")
            print(f"   LEAP & Landmarks:")
            print(f"   http://localhost:{port}/pittsburgh_map_leap_landmarks.html")
            print(f"\n   Jaymars List & Landmarks:")
            print(f"   http://localhost:{port}/pittsburgh_map_jaymars_landmarks.html")
            print(f"\n   Index page (links to both):")
            print(f"   http://localhost:{port}/index.html")
            print(f"\n   Original complete map:")
            print(f"   http://localhost:{port}/pittsburgh_interactive_map.html")
            print(f"{'='*60}\n")
            
            # Open browser to index page
            time.sleep(0.5)
            webbrowser.open(f"http://localhost:{port}/index.html")
            
            print("Server running. Press Ctrl+C to stop.\n")
            # Serve forever (blocking call)
            httpd.serve_forever()
            
    except OSError:
        print(f"Error: Port {port} is already in use. Please stop the other server first.")
    except KeyboardInterrupt:
        print("\n\nServer stopped.")
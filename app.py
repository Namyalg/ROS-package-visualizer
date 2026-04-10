#!/usr/bin/env python3
"""
Flask app for visualizing package.xml dependency graphs
"""

from flask import Flask, render_template, request, jsonify
import xml.etree.ElementTree as ET
import urllib.request
import sys
import re

# Cache for rosdistro
_distro_cache = None

app = Flask(__name__)

# ROS-related keywords to identify ROS packages
ROS_KEYWORDS = {
    'ament_', 'rclcpp', 'rclpy', 'rcl_', 'rosidl_', 'ros2_',
    'geometry_msgs', 'std_msgs', 'sensor_msgs', 'nav_msgs',
    'tf2', 'rviz', 'gazebo', 'pluginlib', 'actionlib', 'ros_environment', 'git'
}

def is_ros_dependency(dep_name):
    """Determine if a dependency is ROS-related based on naming patterns"""
    dep_lower = dep_name.lower()

    # Check for ROS keywords
    if any(keyword in dep_lower for keyword in ROS_KEYWORDS):
        return True

    # Check if it looks like a system library (common pattern)
    if dep_lower.startswith('lib') and '-dev' in dep_lower:
        return False

    # Check if it's a well-known non-ROS library
    non_ros_libs = {'sqlite', 'zmq', 'xml', 'boost', 'opencv', 'pcl', 'eigen', 'yaml', 'vendor'}
    if any(lib in dep_lower for lib in non_ros_libs):
        return False

    # Default: assume ROS if we can't determine
    return True

def fetch_humble_packages():
    """Fetch ROS Humble distribution and get package line mappings"""
    global _distro_cache

    if _distro_cache is not None:
        return _distro_cache

    try:
        url = "https://raw.githubusercontent.com/ros/rosdistro/master/humble/distribution.yaml"
        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read().decode('utf-8')

        # Parse to find package names and their line numbers
        packages = {}
        lines = content.split('\n')
        in_repositories = False

        for line_num, line in enumerate(lines, 1):
            # Check if we've entered the repositories section
            if line.startswith('repositories:'):
                in_repositories = True
                continue

            if in_repositories:
                # Match package definitions (2-space indented, followed by colon)
                match = re.match(r'^  ([a-zA-Z0-9_-]+):\s*$', line)
                if match:
                    pkg_name = match.group(1)
                    packages[pkg_name] = line_num
                # Stop if we hit a non-indented line (end of repositories section)
                elif line and not line.startswith(' ') and not line.startswith('#'):
                    break

        _distro_cache = packages
        return packages
    except Exception as e:
        print(f"Warning: Could not fetch humble packages: {e}", file=sys.stderr)
        return {}

def fetch_package_xml(github_url):
    """Fetch package.xml content from GitHub URL"""
    if 'github.com' in github_url and '/blob/' in github_url:
        parts = github_url.replace('github.com', 'raw.githubusercontent.com').split('/blob/')
        raw_url = parts[0] + '/' + parts[1]
    else:
        raw_url = github_url

    try:
        with urllib.request.urlopen(raw_url, timeout=10) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        raise Exception(f"Error fetching {raw_url}: {str(e)}")

def parse_package_xml(xml_content):
    """Parse package.xml and extract dependencies"""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise Exception(f"Error parsing XML: {str(e)}")

    name = root.findtext('name', 'Unknown')
    version = root.findtext('version', 'Unknown')
    description = root.findtext('description', 'No description')
    maintainer = root.findtext('maintainer', 'Unknown')

    dependencies = {}  # Use dict to track type

    # Parse all dependency types
    for dep in root.findall('buildtool_depend'):
        if dep.text:
            dependencies[dep.text] = 'buildtool_depend'

    for dep in root.findall('build_depend'):
        if dep.text and dep.text not in dependencies:
            dependencies[dep.text] = 'build_depend'

    for dep in root.findall('run_depend'):
        if dep.text and dep.text not in dependencies:
            dependencies[dep.text] = 'run_depend'

    for dep in root.findall('test_depend'):
        if dep.text and dep.text not in dependencies:
            dependencies[dep.text] = 'test_depend'

    for dep in root.findall('exec_depend'):
        if dep.text and dep.text not in dependencies:
            dependencies[dep.text] = 'exec_depend'

    for dep in root.findall('depend'):
        if dep.text and dep.text not in dependencies:
            dependencies[dep.text] = 'depend'

    return {
        'name': name,
        'version': version,
        'description': description,
        'maintainer': maintainer,
        'dependencies': dependencies  # Now returns dict with types
    }

def build_graph_data(package_info):
    """Build graph data for visualization"""
    nodes = []
    edges = []
    node_id = 0
    node_map = {}

    # Fetch humble packages for reference links
    humble_packages = fetch_humble_packages()

    # Add main package node
    nodes.append({
        'id': node_id,
        'label': f"{package_info['name']}\nv{package_info['version']}",
        'title': package_info['description'],
        'color': {'background': 'white', 'border': 'black'},
        'shape': 'diamond',
        'font': {'size': 14},
        'borderWidth': 2
    })
    root_id = node_id
    node_map[package_info['name']] = root_id
    node_id += 1

    # Add dependency nodes with type information
    for dep_name, dep_type in package_info['dependencies'].items():
        is_ros = is_ros_dependency(dep_name)
        in_humble = dep_name in humble_packages

        # Generate humble distro link if package is in distro
        distro_link = None
        if in_humble:
            line_num = humble_packages[dep_name]
            distro_link = f"https://github.com/ros/rosdistro/blob/master/humble/distribution.yaml#L{line_num}"

        nodes.append({
            'id': node_id,
            'label': dep_name,
            'title': f"ROS Dependency" if is_ros else f"Non-ROS Dependency",
            'type': dep_type,
            'color': '#d32f2f' if is_ros else '#1976d2',
            'shape': 'box',
            'font': {'size': 11, 'color': 'white'},
            'borderWidth': 0,
            'in_humble': in_humble,
            'distro_link': distro_link
        })
        node_map[dep_name] = node_id
        node_id += 1

    # Add edges from main package to all dependencies
    for dep_name in package_info['dependencies'].keys():
        edges.append({
            'from': root_id,
            'to': node_map[dep_name],
            'arrows': 'to',
            'color': 'black',
            'smooth': {'type': 'cubicBezier'}
        })

    return {
        'nodes': nodes,
        'edges': edges,
        'stats': {
            'ros_count': sum(1 for d in package_info['dependencies'].keys() if is_ros_dependency(d)),
            'non_ros_count': sum(1 for d in package_info['dependencies'].keys() if not is_ros_dependency(d)),
            'total': len(package_info['dependencies'])
        }
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/visualize', methods=['POST'])
def visualize():
    """API endpoint to fetch and visualize a package.xml"""
    data = request.json
    github_url = data.get('url', '').strip()

    if not github_url:
        return jsonify({'error': 'Please provide a GitHub URL'}), 400

    try:
        xml_content = fetch_package_xml(github_url)
        package_info = parse_package_xml(xml_content)
        graph_data = build_graph_data(package_info)

        return jsonify({
            'success': True,
            'package': package_info,
            'graph': graph_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5001)

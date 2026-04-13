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
    """Fetch ROS Humble distribution and get package info (line numbers, URLs, versions)
    Also maps child packages (listed under release.packages) to their parent repository"""
    global _distro_cache

    if _distro_cache is not None:
        return _distro_cache

    try:
        url = "https://raw.githubusercontent.com/ros/rosdistro/master/humble/distribution.yaml"
        with urllib.request.urlopen(url, timeout=10) as response:
            content = response.read().decode('utf-8')

        # Parse to find package names with their metadata
        packages = {}
        lines = content.split('\n')
        in_repositories = False
        current_package = None
        current_package_line = None
        in_source_section = False
        in_release_section = False
        release_packages = []

        for line_num, line in enumerate(lines, 1):
            # Check if we've entered the repositories section
            if line.startswith('repositories:'):
                in_repositories = True
                continue

            if in_repositories:
                # Match package definitions (2-space indented, followed by colon)
                if re.match(r'^  ([a-zA-Z0-9_-]+):\s*$', line):
                    match = re.match(r'^  ([a-zA-Z0-9_-]+):\s*$', line)
                    current_package = match.group(1)
                    current_package_line = line_num
                    in_source_section = False
                    in_release_section = False
                    release_packages = []
                    packages[current_package] = {
                        'line_num': line_num,
                        'source_url': None,
                        'source_version': None
                    }
                # Check if we're entering the release section
                elif current_package and re.match(r'^    release:\s*$', line):
                    in_release_section = True
                    in_source_section = False
                # Check if we're entering the source section
                elif current_package and re.match(r'^    source:\s*$', line):
                    in_release_section = False
                    in_source_section = True
                # Look for packages list in release section (6-space indented, "- package_name")
                elif current_package and in_release_section and re.match(r'^      - (.+)$', line):
                    match = re.match(r'^      - (.+)$', line)
                    pkg_name = match.group(1).strip()
                    release_packages.append(pkg_name)
                # Look for url in source section (6-space indented)
                elif current_package and in_source_section and re.match(r'^      url: (.+)$', line):
                    match = re.match(r'^      url: (.+)$', line)
                    url_value = match.group(1).strip()
                    packages[current_package]['source_url'] = url_value
                    # Also map child packages to this parent repo
                    for pkg_name in release_packages:
                        if pkg_name not in packages:
                            packages[pkg_name] = {
                                'line_num': None,
                                'source_url': url_value,
                                'source_version': None,
                                'parent_repo': current_package
                            }
                # Look for version in source section (6-space indented)
                elif current_package and in_source_section and re.match(r'^      version: (.+)$', line):
                    match = re.match(r'^      version: (.+)$', line)
                    version_value = match.group(1).strip()
                    packages[current_package]['source_version'] = version_value
                    # Update child packages with version
                    for pkg_name in release_packages:
                        if pkg_name in packages and packages[pkg_name].get('source_version') is None:
                            packages[pkg_name]['source_version'] = version_value
                # Exit source/release section when we hit another section
                elif current_package and (in_source_section or in_release_section) and re.match(r'^    \w+:', line):
                    in_source_section = False
                    in_release_section = False
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

def fetch_ros_package_xml(package_name, humble_packages):
    """Fetch package.xml for a ROS package from its source repository"""
    if package_name not in humble_packages:
        return None

    pkg_info = humble_packages[package_name]
    if isinstance(pkg_info, dict):
        source_url = pkg_info.get('source_url')
        source_version = pkg_info.get('source_version')
    else:
        # Handle legacy format (just line number)
        return None

    if not source_url:
        return None

    # Try common locations for package.xml
    possible_urls = []

    # Convert to raw GitHub URL if needed
    if 'github.com' in source_url:
        # Strip .git suffix if present
        base_url = source_url.rstrip('.git').replace('github.com', 'raw.githubusercontent.com')
        if source_url.endswith('.git'):
            base_url = source_url[:-4].replace('github.com', 'raw.githubusercontent.com')

        branch = source_version if source_version else 'master'

        # Try root level
        possible_urls.append(f"{base_url}/{branch}/package.xml")
        # Try package subdirectory
        possible_urls.append(f"{base_url}/{branch}/{package_name}/package.xml")

    # Try each possible URL
    for url in possible_urls:
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                content = response.read().decode('utf-8')
                return content
        except:
            continue

    return None

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

    # Add dependency nodes with type information (without fetching details for speed)
    for dep_name, dep_type in package_info['dependencies'].items():
        is_ros = is_ros_dependency(dep_name)
        in_humble = dep_name in humble_packages

        # For initial visualization, only include basic info
        # Detailed repo info will be fetched on-demand when expanding
        distro_link = None
        if in_humble:
            pkg_info = humble_packages[dep_name]
            if isinstance(pkg_info, dict):
                line_num = pkg_info.get('line_num')
                if line_num:
                    distro_link = f"https://github.com/ros/rosdistro/blob/master/humble/distribution.yaml#L{line_num}"
            else:
                # Handle legacy format (just line number)
                distro_link = f"https://github.com/ros/rosdistro/blob/master/humble/distribution.yaml#L{pkg_info}"

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
            'distro_link': distro_link,
            'is_ros': is_ros
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

def _get_all_repo_dependencies(package_name, humble_packages):
    """Get combined dependencies from all packages in a multi-package repo.
    Returns dict with dependency info and source packages."""
    # Find if this package is part of a multi-package repo
    pkg_info = humble_packages.get(package_name, {})

    # Determine the parent repo entry
    parent_repo = None
    if isinstance(pkg_info, dict):
        parent_repo = pkg_info.get('parent_repo')

    # If it's a child package, use parent; otherwise use the package itself as the repo entry
    repo_entry = parent_repo if parent_repo else package_name

    # Parse all package.xml files in the repo
    all_dependencies = {}  # {dep_name: {type, source_packages: [list]}}
    repo_info = humble_packages.get(repo_entry, {})

    # Get the source URL and version
    if not isinstance(repo_info, dict):
        return all_dependencies

    source_url = repo_info.get('source_url')
    source_version = repo_info.get('source_version', 'master')

    if not source_url:
        return all_dependencies

    # Strip .git suffix if present
    base_url = source_url[:-4].replace('github.com', 'raw.githubusercontent.com') if source_url.endswith('.git') else source_url.replace('github.com', 'raw.githubusercontent.com')

    # Build list of all packages in this repo (from distribution.yaml)
    packages_to_check = []

    # The repo entry itself (always check it)
    packages_to_check.append(repo_entry)

    # Any child packages listed under this repo
    for pkg_name_check, pkg_data in humble_packages.items():
        if isinstance(pkg_data, dict) and pkg_data.get('parent_repo') == repo_entry:
            if pkg_name_check not in packages_to_check:
                packages_to_check.append(pkg_name_check)

    # Fetch and parse each package.xml
    for pkg in packages_to_check:
        url = f"{base_url}/{source_version}/{pkg}/package.xml"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                content = response.read().decode('utf-8')
                pkg_data = parse_package_xml(content)
                # Merge dependencies and track which package it came from
                for dep_name, dep_type in pkg_data['dependencies'].items():
                    if dep_name not in all_dependencies:
                        all_dependencies[dep_name] = {
                            'type': dep_type,
                            'source_packages': []
                        }
                    # Track source package
                    if pkg not in all_dependencies[dep_name]['source_packages']:
                        all_dependencies[dep_name]['source_packages'].append(pkg)
                    # Update type (later ones override)
                    all_dependencies[dep_name]['type'] = dep_type
        except:
            # Try root level if subdirectory fails (though unlikely)
            try:
                url = f"{base_url}/{source_version}/package.xml"
                with urllib.request.urlopen(url, timeout=10) as response:
                    content = response.read().decode('utf-8')
                    pkg_data = parse_package_xml(content)
                    for dep_name, dep_type in pkg_data['dependencies'].items():
                        if dep_name not in all_dependencies:
                            all_dependencies[dep_name] = {
                                'type': dep_type,
                                'source_packages': []
                            }
                        if pkg not in all_dependencies[dep_name]['source_packages']:
                            all_dependencies[dep_name]['source_packages'].append(pkg)
                        all_dependencies[dep_name]['type'] = dep_type
            except:
                continue

    return all_dependencies

@app.route('/api/get-dependencies', methods=['POST'])
def get_dependencies():
    """API endpoint to fetch recursive dependencies for a ROS package"""
    data = request.json
    package_name = data.get('package_name', '').strip()
    visited = data.get('visited', [])

    if not package_name:
        return jsonify({'error': 'Please provide a package name'}), 400

    # Check for circular dependencies
    if package_name in visited:
        return jsonify({
            'success': True,
            'dependencies': [],
            'is_circular': True,
            'message': 'Circular dependency detected'
        })

    # Fetch humble packages info
    humble_packages = fetch_humble_packages()

    # Check if package is in ROS Humble
    if package_name not in humble_packages:
        return jsonify({
            'success': True,
            'dependencies': [],
            'in_humble': False,
            'message': f'Package {package_name} not found in ROS Humble'
        })

    # Fetch package.xml for this package
    xml_content = fetch_ros_package_xml(package_name, humble_packages)
    if not xml_content:
        return jsonify({
            'success': True,
            'dependencies': [],
            'message': f'Could not fetch package.xml for {package_name}'
        })

    # Parse dependencies from primary package
    try:
        package_info = parse_package_xml(xml_content)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error parsing package.xml: {str(e)}'
        }), 400

    # Get all dependencies (including from other packages in multi-package repo)
    all_dependencies = _get_all_repo_dependencies(package_name, humble_packages)

    # Determine if this is a multi-package repo
    pkg_info_val = humble_packages.get(package_name, {})
    is_multi_package = False
    if isinstance(pkg_info_val, dict) and pkg_info_val.get('parent_repo'):
        # This is a child package
        is_multi_package = True
    else:
        # Check if there are any child packages under this repo
        for other_pkg, other_data in humble_packages.items():
            if isinstance(other_data, dict) and other_data.get('parent_repo') == package_name:
                is_multi_package = True
                break

    # If we got repo-wide dependencies, use those; otherwise use just this package
    if all_dependencies:
        dependencies_to_use = all_dependencies
    else:
        # Convert simple dependencies to new format
        dependencies_to_use = {
            dep_name: {'type': dep_type, 'source_packages': [package_name]}
            for dep_name, dep_type in package_info['dependencies'].items()
        }

    # Build response with ROS dependencies only
    dependencies = []
    for dep_name, dep_info in dependencies_to_use.items():
        if is_ros_dependency(dep_name):
            # Handle both old format (just type) and new format (dict with type and source_packages)
            if isinstance(dep_info, str):
                dep_type = dep_info
                source_packages = [package_name]
            else:
                dep_type = dep_info.get('type', 'depend')
                source_packages = dep_info.get('source_packages', [package_name])

            # Get repo URL if available
            repo_url = None
            pkg_info_dep = humble_packages.get(dep_name, {})
            if isinstance(pkg_info_dep, dict):
                repo_url = pkg_info_dep.get('source_url')

            # Get distro link
            distro_link = None
            if isinstance(pkg_info_dep, dict):
                line_num = pkg_info_dep.get('line_num')
                if line_num:
                    distro_link = f"https://github.com/ros/rosdistro/blob/master/humble/distribution.yaml#L{line_num}"

            dep_obj = {
                'name': dep_name,
                'type': dep_type,
                'is_ros': True,
                'repo_url': repo_url,
                'distro_link': distro_link
            }

            # Add source_packages if this is a multi-package repo
            if is_multi_package and source_packages:
                dep_obj['source_packages'] = source_packages

            dependencies.append(dep_obj)

    return jsonify({
        'success': True,
        'dependencies': dependencies,
        'package_info': {
            'name': package_info['name'],
            'version': package_info['version'],
            'description': package_info['description']
        }
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)

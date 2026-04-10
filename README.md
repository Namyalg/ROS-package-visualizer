# ROS-package-visualizer

A minimal web-based tool to visualize ROS 2 package dependencies as a tree structure with ROS Humble integration.

## Usage

```bash
chmod +x start.sh
./start.sh
```

Open: **http://localhost:5001**

Paste any GitHub URL to a `package.xml` file and click **Visualize**.

## Features

- ✅ Tree-structured dependency view
- ✅ ROS (red) vs non-ROS (blue) classification
- ✅ Dependency type labels (build & runtime, runtime only, test only, build tool)
- ✅ **ROS Humble integration** - packages in Humble have a `↗` link to their definition
- ✅ Click links to view packages in the official ROS Humble distribution
- ✅ Support for branches and commits
- ✅ Minimal black & white design
- ✅ Easy scrolling for large dependency lists

## ROS Humble Integration

When a dependency is found in the official ROS Humble distribution, a `↗` link appears next to its name. Click it to jump to that package's definition in the [rosdistro repository](https://github.com/ros/rosdistro/blob/master/humble/distribution.yaml).

**Currently supports 826 packages** from ROS Humble.

## Stop

Press **Ctrl+C** in the terminal.

## Usage

1. **Enter a GitHub URL** to any `package.xml` file:
   - Branch: `https://github.com/BehaviorTree/BehaviorTree.CPP/blob/master/package.xml`
   - Specific commit: `https://github.com/BehaviorTree/BehaviorTree.CPP/blob/e6754eeb550f0c76b82da42e377a4d807ce51a6b/package.xml`

2. **Click "Visualize"** or press Enter

3. **Explore the graph**:
   - Scroll to zoom in/out
   - Drag to pan
   - Click and drag nodes to rearrange

## Architecture

### Backend (`app.py`)
- Flask web server
- Parses package.xml from GitHub
- Builds dependency graph structure
- Classifies dependencies (ROS vs non-ROS)

### Frontend (`templates/index.html`)
- HTML5 interface
- Real-time API communication
- vis.js graph visualization

### Styling (`static/style.css`)
- Modern gradient design
- Responsive layout for all devices

## Dependency Classification

The tool automatically classifies dependencies based on naming patterns:

**ROS Dependencies (Green):**
- `ament_*` - ROS 2 build tools
- `rclcpp` / `rclpy` - ROS 2 client libraries
- `ros_*` - ROS packages
- `geometry_msgs`, `std_msgs`, etc. - ROS message types

**Non-ROS Dependencies (Blue):**
- `libsqlite3-dev` - Database libraries
- `libzmq3-dev` - Message queues
- `tinyxml2` - XML parsers
- Standard C++ libraries

## Graph Visualization

- **Golden Diamond** - Main package
- **Green Boxes** - ROS dependencies
- **Blue Boxes** - Non-ROS dependencies
- Edges show dependency relationships

## Project Structure

```
package_xml_visualizer/
├── app.py                    # Flask backend
├── requirements.txt          # Python dependencies
├── templates/
│   └── index.html           # Web UI
├── static/
│   └── style.css            # Styling
├── visualizer.py            # CLI tool (legacy)
└── README.md
```

## Requirements

- Python 3.7+
- Flask 2.3+

## Examples

### BehaviorTree.CPP
```bash
# The app loads this by default
https://github.com/BehaviorTree/BehaviorTree.CPP/blob/master/package.xml
```

## Troubleshooting

**Port Already in Use:**
```bash
python3 app.py --port 5001
```

**Cannot Fetch Package.xml:**
- Ensure the URL points to a valid package.xml file
- Check your internet connection
- Verify the GitHub repository exists and is public

## Notes

- The visualizer uses vis.js for graph rendering
- Graphs are optimized with hierarchical layout
- Physics simulation helps arrange nodes automatically
- All communication is done client-side when possible

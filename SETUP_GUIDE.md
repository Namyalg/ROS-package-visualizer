# Package.XML Visualizer - Complete Setup Guide

This guide will help you set up and run the Package.XML Dependency Visualizer on macOS or Linux.

## Installation & Setup

### Step 1: Clone or Download the Project

```bash
cd /path/to/package_xml_visualizer
```

### Step 2: Run the Automatic Setup Script

```bash
chmod +x setup.sh
./setup.sh
```

The script will:
- ✓ Check for Python 3
- ✓ Create a virtual environment
- ✓ Install all required dependencies
- ✓ Show you how to run the app

### Step 3: Activate the Virtual Environment

```bash
source venv/bin/activate
```

You should see `(venv)` at the start of your terminal prompt.

### Step 4: Start the Application

```bash
python3 app.py
```

You should see output like:
```
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

### Step 5: Open in Your Browser

Go to: **http://localhost:5000**

---

### Manual Setup (If Script Fails)

If the automatic setup script fails, you can manually set everything up:

#### 1. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

#### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Run the App

```bash
python3 app.py
```

---

## Usage

### Basic Workflow

1. **Enter a GitHub URL** to any `package.xml` file
   - You can use any branch or specific commit
   - Example: `https://github.com/BehaviorTree/BehaviorTree.CPP/blob/master/package.xml`

2. **Click "Visualize"** or press Enter

3. **Explore the graph**:
   - **Scroll** to zoom in/out
   - **Drag** to pan around
   - **Click and drag nodes** to rearrange them
   - **Hover over nodes** to see more information

### Understanding the Graph

- **Golden Diamond** = Your main package
- **Green Boxes** = ROS-related dependencies (ament_*, rclcpp, etc.)
- **Blue Boxes** = Non-ROS dependencies (SQLite, ZeroMQ, XML libraries, etc.)
- **Lines (Edges)** = Dependency relationships

### Finding Package.xml URLs

ROS packages on GitHub typically have a `package.xml` at the root:

Examples:
- Main branch: `https://github.com/org/repo/blob/main/package.xml`
- Master branch: `https://github.com/org/repo/blob/master/package.xml`
- Specific commit: `https://github.com/org/repo/blob/abc123def/package.xml`

---

## Troubleshooting

### Problem: Port 5000 Already in Use

If you get an error about port 5000 being in use:

**Quick Fix:**
```bash
# Find and kill the process using port 5000
lsof -ti:5000 | xargs kill -9
```

**Alternative:**
Edit `app.py` and change the port:
```python
if __name__ == '__main__':
    app.run(debug=True, port=5001)  # Change 5000 to 5001
```

### Problem: "No module named 'flask'"

This means the virtual environment is not activated or dependencies aren't installed:

```bash
# Activate venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate.bat # Windows

# Install dependencies
pip install -r requirements.txt
```

### Problem: Cannot Fetch Package.xml

**Possible causes:**
1. URL is incorrect - verify the package.xml exists on GitHub
2. No internet connection - check your connection
3. GitHub is down - try again later
4. Private repository - the repo must be public

**Solution:**
1. Test the URL in your browser
2. Check your internet connection
3. Ensure the repository is public

### Problem: Graph Not Displaying

**Try:**
1. Refresh the page (Ctrl+R or Cmd+R)
2. Clear browser cache
3. Try a different browser
4. Check browser console for errors (F12)

---

## Stopping the Application

To stop the Flask server:

1. In the terminal where it's running, press **Ctrl+C**
2. The server will shut down

To deactivate the virtual environment:

```bash
deactivate
```

---

## Project Structure

```
package_xml_visualizer/
├── app.py                    # Flask backend server
├── requirements.txt          # Python package dependencies
├── setup.sh                  # macOS/Linux automatic setup
├── setup.bat                 # Windows automatic setup
├── .gitignore               # Git ignore file
├── README.md                # User-friendly documentation
├── SETUP_GUIDE.md           # This file
├── templates/
│   └── index.html           # Web interface
└── static/
    └── style.css            # Styling and layout
```

---

## Advanced Usage

### Running on a Network

If you want to access the visualizer from another computer:

1. Find your computer's IP address:
   - **macOS/Linux:** `ifconfig` (look for inet)
   - **Windows:** `ipconfig` (look for IPv4)

2. Edit `app.py` and change:
   ```python
   app.run(debug=True, port=5000)
   ```
   to:
   ```python
   app.run(debug=True, host='0.0.0.0', port=5000)
   ```

3. Access from other computers using:
   ```
   http://<your-ip>:5000
   ```

### Running Without Debug Mode

For production use, disable debug mode in `app.py`:

```python
if __name__ == '__main__':
    app.run(debug=False, port=5000)
```

---

## Getting Help

If you encounter issues:

1. **Check the terminal output** for error messages
2. **Verify your internet connection**
3. **Try the troubleshooting section above**
4. **Check that Python 3.7+ is installed:** `python3 --version`
5. **Verify Flask is installed:** `pip list | grep Flask`

---

## Next Steps

Once you have the visualizer running:

1. Try different package.xml files from various GitHub repositories
2. Analyze dependency patterns in ROS projects
3. Share URLs with team members to discuss dependencies
4. Use it to understand package structures before diving into code

---

Happy visualizing! 🚀

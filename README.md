# TrackPy

A simple command-line time tracking application to help you track your work, study, and other activities.

## Installation

1. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install the application:
```bash
pip install -e .
```

## Usage

After installation, you can use the `trackpy` command directly from anywhere in your terminal:

### Start tracking an activity
```bash
trackpy start "Writing code" -c work
```

### Stop the current activity
```bash
trackpy stop
```

### Generate reports
```bash
trackpy report  # Today's report
trackpy report -p week  # Weekly report
trackpy report -p month  # Monthly report
trackpy report -p all  # All-time report
trackpy report -c work  # Filter by category
```

### Clear all tracking data
```bash
trackpy clear        # Clear with confirmation prompt
trackpy clear -f     # Force clear without confirmation
```

## Features

- Track multiple activities with categories (work, study, personal)
- Start and stop tracking
- Generate reports for different time periods
- Filter reports by category
- Beautiful terminal output with live tracking animation
- Clear tracking history with safety confirmation

#!/usr/bin/env python3

import click
import sqlite3
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.columns import Columns
from rich.layout import Layout
from dateutil import parser
from dateutil.relativedelta import relativedelta
import time
import threading
import signal
import sys
from zoneinfo import ZoneInfo
import platform
import subprocess

console = Console()
stop_tracking = threading.Event()

def format_duration(seconds):
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def get_system_timezone():
    """Get the system timezone."""
    if platform.system() == 'Darwin':  # macOS
        try:
            output = subprocess.check_output(['systemsetup', '-gettimezone']).decode()
            return output.split(': ')[1].strip()
        except:
            return 'UTC'
    return 'UTC'

def tracking_animation(activity, category, start_time):
    with Live(refresh_per_second=1) as live:
        while not stop_tracking.is_set():
            duration = int((datetime.now() - start_time).total_seconds())
            formatted_duration = format_duration(duration)
            
            panel_content = Text()
            panel_content.append("🕒 Currently tracking\n", style="bold green")
            panel_content.append(f"Activity: ", style="bold")
            panel_content.append(f"{activity}\n", style="cyan")
            panel_content.append(f"Category: ", style="bold")
            panel_content.append(f"{category}\n", style="yellow")
            panel_content.append(f"Duration: ", style="bold")
            panel_content.append(formatted_duration, style="red")
            
            panel = Panel(
                Align.center(panel_content),
                title="[bold]TrackPy[/bold]",
                border_style="green"
            )
            
            live.update(panel)
            time.sleep(1)

def signal_handler(signum, frame):
    stop_tracking.set()
    console.print("\n[yellow]Stopping tracking... Use 'trackpy stop' to save the session.[/yellow]")
    sys.exit(0)

def init_db():
    conn = sqlite3.connect('timetrack.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity TEXT NOT NULL,
            category TEXT NOT NULL,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            duration INTEGER
        )
    ''')
    conn.commit()
    conn.close()

@click.group()
def cli():
    """Time tracking application for work, study, and other activities."""
    init_db()

@cli.command()
@click.argument('activity')
@click.option('--category', '-c', default='work', help='Category of the activity (work/study/personal)')
def start(activity, category):
    """Start tracking an activity."""
    conn = sqlite3.connect('timetrack.db')
    c = conn.cursor()
    
    # Check if there's any ongoing activity
    c.execute('SELECT * FROM activities WHERE end_time IS NULL')
    ongoing = c.fetchone()
    if ongoing:
        console.print(f"[red]Error: Activity '{ongoing[1]}' is still ongoing. Stop it first.[/red]")
        return

    now = datetime.now()
    c.execute('''
        INSERT INTO activities (activity, category, start_time)
        VALUES (?, ?, ?)
    ''', (activity, category, now))
    
    conn.commit()
    conn.close()

    # Set up signal handler for graceful exit
    signal.signal(signal.SIGINT, signal_handler)
    
    # Reset the stop event
    stop_tracking.clear()
    
    console.print(f"[green]Started tracking: {activity} ({category})[/green]")
    console.print("[yellow]Press Ctrl+C to stop tracking[/yellow]")
    
    # Start the tracking animation
    tracking_animation(activity, category, now)

@cli.command()
def stop():
    """Stop tracking the current activity."""
    conn = sqlite3.connect('timetrack.db')
    c = conn.cursor()
    
    c.execute('SELECT * FROM activities WHERE end_time IS NULL')
    activity = c.fetchone()
    
    if not activity:
        console.print("[red]No activity is currently being tracked.[/red]")
        return

    now = datetime.now()
    duration = (now - parser.parse(activity[3])).seconds // 60  # Duration in minutes
    
    c.execute('''
        UPDATE activities 
        SET end_time = ?, duration = ?
        WHERE id = ?
    ''', (now, duration, activity[0]))
    
    conn.commit()
    conn.close()
    console.print(f"[green]Stopped tracking: {activity[1]} (Duration: {duration} minutes)[/green]")

def create_bar_chart(activities, max_width=40):
    """Create a bar chart visualization of activities."""
    if not activities:
        return Text("No data available")
    
    # Find the maximum duration for scaling
    max_duration = max(sum(session[4] for session in sessions) for activity, category, sessions in activities)
    
    chart = Text()
    chart.append("📊 Time Distribution\n\n", style="bold cyan")
    
    # Calculate bar lengths and create bars
    for activity, category, sessions in activities:
        # Calculate total duration for activity
        total_duration = sum(session[4] for session in sessions)
        
        # Calculate bar length
        bar_length = int((total_duration / max_duration) * max_width)
        bar = "█" * bar_length
        
        # Add category color based on name
        if category.lower() == 'work':
            color = "blue"
        elif category.lower() == 'study':
            color = "green"
        else:
            color = "yellow"
        
        # Format duration in hours and minutes
        hours = total_duration // 60
        minutes = total_duration % 60
        duration_str = f"{hours}h {minutes}m"
        
        # Create the bar line
        chart.append(f"{activity[:20]:<20} ")
        chart.append(bar, style=color)
        chart.append(f" {duration_str}\n")
    
    return Panel(chart, title="[bold]Activity Distribution[/bold]", border_style="cyan")

@cli.command()
@click.option('--period', '-p', default='today', 
              type=click.Choice(['today', 'week', 'month', 'all']),
              help='Time period for the report')
@click.option('--category', '-c', help='Filter by category')
def report(period, category):
    """Generate a time tracking report."""
    conn = sqlite3.connect('timetrack.db')
    c = conn.cursor()

    now = datetime.now()
    timezone = get_system_timezone()
    
    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_str = "Today's Activity"
    elif period == 'week':
        start_date = now - relativedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        period_str = "This Week's Activity"
    elif period == 'month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_str = "This Month's Activity"
    else:  # all
        start_date = datetime.min
        period_str = "All-Time Activity"

    if category:
        period_str += f" ({category})"

    # First, get all activities with their categories
    query = '''
        SELECT DISTINCT activity, category
        FROM activities
        WHERE end_time IS NOT NULL
        AND start_time >= ?
    '''
    params = [start_date]

    if category:
        query += ' AND category = ?'
        params.append(category)

    c.execute(query, params)
    activities_list = c.fetchall()

    # For each activity, get its sessions
    activities_data = []
    for activity, category in activities_list:
        session_query = '''
            SELECT activity, category, start_time, end_time, duration
            FROM activities
            WHERE activity = ? AND category = ?
            AND end_time IS NOT NULL
            AND start_time >= ?
            ORDER BY start_time DESC
        '''
        session_params = [activity, category, start_date]
        c.execute(session_query, session_params)
        sessions = c.fetchall()
        activities_data.append((activity, category, sessions))

    # Sort activities by total duration
    activities_data.sort(key=lambda x: sum(session[4] for session in x[2]), reverse=True)

    # Create the table
    table = Table(show_header=True, header_style="bold magenta", title=period_str, title_style="bold cyan")
    table.add_column("Activity")
    table.add_column("Category")
    table.add_column("Session Time")
    table.add_column("Duration")

    for activity, category, sessions in activities_data:
        # Add a row for each session
        first_row = True
        for session in sessions:
            start_time = parser.parse(session[2]).astimezone(ZoneInfo(timezone))
            end_time = parser.parse(session[3]).astimezone(ZoneInfo(timezone))
            duration = session[4]
            
            # Format duration
            hours = duration // 60
            minutes = duration % 60
            duration_str = f"{hours}h {minutes}m"
            
            # Format session time
            session_time = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
            if start_time.date() != end_time.date():
                session_time = f"{start_time.strftime('%Y-%m-%d %H:%M')} - {end_time.strftime('%Y-%m-%d %H:%M')}"
            
            table.add_row(
                activity if first_row else "",
                Text(category, style="bold " + ("blue" if category.lower() == "work" else "green" if category.lower() == "study" else "yellow")) if first_row else "",
                session_time,
                duration_str
            )
            first_row = False
        
        # Add a separator between activities
        if sessions:
            table.add_row("", "", "", "")

    # Create layout with table and chart side by side
    layout = Layout()
    layout.split_column(
        Layout(Panel(table, border_style="cyan")),
        Layout(create_bar_chart(activities_data))
    )

    console.print(layout)
    
    # Print total time
    total_minutes = sum(sum(session[4] for session in sessions) for _, _, sessions in activities_data)
    total_hours = total_minutes // 60
    remaining_minutes = total_minutes % 60
    console.print(f"\n[bold cyan]Total Time:[/bold cyan] [bold]{total_hours}h {remaining_minutes}m[/bold]")

    conn.close()

@cli.command()
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompt')
def clear(force):
    """Clear all tracking data."""
    if not force:
        if not click.confirm('[red]⚠️  Warning: This will delete all tracking data. Are you sure?[/red]', default=False):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return

    conn = sqlite3.connect('timetrack.db')
    c = conn.cursor()
    
    # Get count of records before deletion
    c.execute('SELECT COUNT(*) FROM activities')
    count = c.fetchone()[0]
    
    # Delete all records
    c.execute('DELETE FROM activities')
    conn.commit()
    conn.close()
    
    console.print(f"[green]✓ Successfully cleared {count} tracking records.[/green]")

if __name__ == '__main__':
    cli()

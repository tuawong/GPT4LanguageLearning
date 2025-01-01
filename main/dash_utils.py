# Import packages
import dash
from dash import Dash, html, dash_table, callback, Output, Input, State
from main.translation import *
import pandas as pd
import dash_bootstrap_components as dbc

from dash import dcc

def create_tabs(tab_labels, tab_ids, id, container_style=None, tab_style=None, selected_tab_style=None):
    """
    Utility function to create styled tabs for Dash.
    
    Parameters:
    - tab_labels (list of str): List of labels for the tabs.
    - tab_ids (list of str): List of unique IDs for the tabs.
    - container_style (dict): Styling for the tab container.
    - tab_style (dict): Styling for individual tabs (non-selected).
    - selected_tab_style (dict): Styling for the selected tab.
    
    Returns:
    - dcc.Tabs: A Dash Tabs component with the specified tabs and styles.
    """
    # Default styles
    default_container_style = {
        'width': '50%',
        'margin': 'auto',
        'border': '1px solid #dee2e6',
        'borderRadius': '5px',
    }
    default_tab_style = {
        'backgroundColor': '#f8f9fa',
        'color': '#6c757d',
        'padding': '10px',
        'border': '1px solid #dee2e6',
    }
    default_selected_tab_style = {
        'backgroundColor': '#007bff',
        'color': 'white',
        'fontWeight': 'bold',
        'padding': '10px',
        'borderBottom': '3px solid #0056b3',
    }

    # Apply user-defined styles or fallback to defaults
    container_style = container_style or default_container_style
    tab_style = tab_style or default_tab_style
    selected_tab_style = selected_tab_style or default_selected_tab_style

    # Create tabs dynamically
    tabs = [
        dcc.Tab(label=label, value=tab_id, style=tab_style, selected_style=selected_tab_style)
        for label, tab_id in zip(tab_labels, tab_ids)
    ]

    return dcc.Tabs(id=id, value=tab_ids[0], children=tabs, style=container_style)

# gui_manager.py

import dearpygui.dearpygui as dpg
from datetime import datetime
import json

dpg.create_context()

# Color palette
COLOR_BG = (0, 0, 0)      # 023E7D
COLOR_TAB = (0, 40, 85)      # 002855
COLOR_TAB_ACTIVE = (0, 24, 69) # 001845
COLOR_TAB_HOVER = (0, 18, 51) # 001233
COLOR_HEADER = (51, 65, 92)  # 33415C
COLOR_TEXT = (255, 255, 255) 
COLOR_INPUT = (92, 103, 125) # 5C677D
COLOR_BORDER = (92, 103, 125) # 5C677D
COLOR_ACCENT = (2, 62, 125)  # 023E7D

# Global variables for statistics
token_count = 0
honeypot_count = 0
high_liquidity_count = 0

def setup_historical_data_handlers():
    try:
        dpg.set_value("history_search", "")
        dpg.set_value("history_honeypot_filter", False)
        dpg.configure_item("history_search", callback=filter_historical_data)
        dpg.configure_item("history_honeypot_filter", callback=filter_historical_data)
    except Exception as e:
        print(f"Error setting up historical data handlers: {e}")

def setup_gui():
    # Load and set custom font
    with dpg.font_registry():
        default_font = dpg.add_font("resources/fonts/Heebo/static/Heebo-Bold.ttf", 18)
    dpg.bind_font(default_font)

    # Setup theme
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, COLOR_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, COLOR_TAB)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, COLOR_TAB)
            dpg.add_theme_color(dpg.mvThemeCol_Border, COLOR_BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, COLOR_INPUT)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, COLOR_TAB_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, COLOR_TAB_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, COLOR_HEADER)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, COLOR_ACCENT)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, COLOR_HEADER)
            dpg.add_theme_color(dpg.mvThemeCol_Tab, COLOR_TAB)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, COLOR_TAB_ACTIVE)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, COLOR_TAB_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255))  # Set text color to pure white
            dpg.add_theme_color(dpg.mvThemeCol_Button, COLOR_HEADER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, COLOR_TAB_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, COLOR_TAB_ACTIVE)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 10)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 8)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 10, 8)
    dpg.bind_theme(global_theme)

    # Main window
    with dpg.window(label="UNISWAP Token Tracker", width=1000, height=800):
        # Header with status and statistics
        with dpg.group(horizontal=True):
            dpg.add_text("Status: Starting...", tag="status")
            dpg.add_spacer(width=50)
            dpg.add_text("Tokens Detected: 0", tag="token_stats")
            dpg.add_spacer(width=20)
            dpg.add_text("Honeypots: 0", tag="honeypot_stats")
            dpg.add_spacer(width=20)
            dpg.add_text("High Liquidity: 0", tag="liquidity_stats")
        
        dpg.add_separator()

        # Main content tabs
        with dpg.tab_bar():
            # Token Events Tab
            with dpg.tab(label="Token Events"):
                with dpg.group():
                    # Filters
                    with dpg.group(horizontal=True):
                        dpg.add_checkbox(label="Show Honeypots Only", tag="honeypot_filter")
                        dpg.add_checkbox(label="High Liquidity Only", tag="liquidity_filter")
                        dpg.add_input_text(label="Search", width=200, tag="token_search")
                    
                    dpg.add_separator()
                    
                    # Token list with columns
                    with dpg.child_window(height=300):
                        with dpg.table(header_row=True, resizable=True,
                                     borders_innerH=True, borders_outerH=True,
                                     borders_innerV=True, borders_outerV=True,
                                     tag="token_table") as token_table:
                            dpg.add_table_column(label="Time", width=80)
                            dpg.add_table_column(label="Token Address", width=250)
                            dpg.add_table_column(label="Liquidity (ETH)", width=100)
                            dpg.add_table_column(label="Honeypot", width=80)
                            dpg.add_table_column(label="Ownership", width=120)
                    
                    dpg.add_child_window(height=400, tag="token_log_window")
            
            # Wallet Alerts Tab
            with dpg.tab(label="Wallet Alerts"):
                with dpg.group():
                    dpg.add_text("Monitored Wallets Activity:")
                    dpg.add_child_window(height=400, tag="wallet_log_window")
            
            # Historical Data Tab
            with dpg.tab(label="Historical Data"):
                with dpg.group():
                    with dpg.group(horizontal=True):
                        dpg.add_input_text(label="Search", width=200, tag="history_search")
                        dpg.add_checkbox(label="Show Honeypots Only", tag="history_honeypot_filter")
                    
                    with dpg.child_window(height=500):
                        with dpg.table(header_row=True, resizable=True,
                                     borders_innerH=True, borders_outerH=True,
                                     borders_innerV=True, borders_outerV=True,
                                     tag="history_table") as history_table:
                            dpg.add_table_column(label="Date/Time", width=120)
                            dpg.add_table_column(label="Token Name", width=120)
                            dpg.add_table_column(label="Token Address", width=250)
                            dpg.add_table_column(label="Pair Address", width=250)
                            dpg.add_table_column(label="Liquidity (ETH)", width=100)
                            dpg.add_table_column(label="Honeypot", width=80)
                            dpg.add_table_column(label="Ownership", width=120)

            # Analytics Tab
            with dpg.tab(label="Analytics"):
                with dpg.plot(label="Token Statistics", height=300, width=-1):
                    dpg.add_plot_axis(dpg.mvXAxis, label="Time")
                    dpg.add_plot_axis(dpg.mvYAxis, label="Count", tag="y_axis")
                    dpg.add_line_series([], [], label="New Tokens", parent="y_axis", tag="token_plot")
                    dpg.add_line_series([], [], label="Honeypots", parent="y_axis", tag="honeypot_plot")

    dpg.create_viewport(title='UNISWAP Tracker', width=1000, height=800)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    
    setup_historical_data_handlers()
    filter_historical_data()

def update_token_log(token_info: dict):
    global token_count, honeypot_count, high_liquidity_count
    try:
        # Update statistics
        token_count += 1
        if token_info.get('honeypot', False):
            honeypot_count += 1
        if token_info.get('liquidity_eth', 0) > 5:  # Consider high liquidity if > 5 ETH
            high_liquidity_count += 1
        
        # Update stats display
        dpg.configure_item("token_stats", default_value=f"Tokens Detected: {token_count}")
        dpg.configure_item("honeypot_stats", default_value=f"Honeypots: {honeypot_count}")
        dpg.configure_item("liquidity_stats", default_value=f"High Liquidity: {high_liquidity_count}")
        
        # Add row to token table
        with dpg.table_row(parent="token_table"):
            dpg.add_text(datetime.now().strftime("%H:%M:%S"))
            dpg.add_text(token_info.get('address', 'N/A')[:22] + "...")  # Truncate long addresses
            dpg.add_text(f"{token_info.get('liquidity_eth', 0):.2f}")
            dpg.add_text(" Yes" if token_info.get('honeypot', False) else "No")
            dpg.add_text(" Renounced" if token_info.get('ownership_renounced', False) else " Not Renounced")
    except Exception as e:
        print(f"GUI Update Error: {e}")  # This will help debug any of my GUI issues
    
    # log infor
    detail_text = (
        f"Token: {token_info.get('address', 'N/A')}\n"
        f"Liquidity: {token_info.get('liquidity_eth', 0):.2f} ETH\n"
        f"Honeypot: {'Yes' if token_info.get('honeypot', False) else 'No'}\n"
        f"Ownership: {'Renounced' if token_info.get('ownership_renounced', False) else 'Not Renounced'}\n"
        f"------------------------"
    )
    dpg.add_text(detail_text, parent="token_log_window")

def update_wallet_log(message: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    dpg.add_text(f"[{timestamp}] {message}", parent="wallet_log_window")

def update_status(message: str):
    dpg.set_value("status", f"Status: {message}")

def render_gui():
    print("GUI thread started")
    while dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()

def filter_historical_data(sender=None, value=None):
    try:
        with open("logs/tokens.json", "r") as f:
            historical_data = json.load(f)
            
        # Get filter values
        search_text = dpg.get_value("history_search").lower()
        show_honeypots = dpg.get_value("history_honeypot_filter")
            
        # Clear existing rows
        for child in dpg.get_item_children("history_table", slot=1):
            dpg.delete_item(child)
            
        # Add historical data to the table
        for entry in historical_data:
            token0 = entry.get("token0", {})
            token1 = entry.get("token1", {})
            
            # Only show tokens paired with WETH/ETH
            if token1.get("symbol") in ["WETH", "ETH"]:
                main_token = token0
            elif token0.get("symbol") in ["WETH", "ETH"]:
                main_token = token1
            else:
                continue
                
            # Apply filters
            if show_honeypots and not entry.get("honeypot", False):
                continue
                
            token_name = f"{main_token.get('name', 'Unknown')} ({main_token.get('symbol', 'N/A')})".lower()
            token_address = main_token.get("address", "").lower()
            
            if search_text and search_text not in token_name and search_text not in token_address:
                continue
                
            with dpg.table_row(parent="history_table"):
                timestamp = datetime.fromisoformat(entry.get("timestamp", "").rstrip('Z'))
                dpg.add_text(timestamp.strftime("%Y-%m-%d %H:%M"))
                dpg.add_text(f"{main_token.get('name', 'Unknown')} ({main_token.get('symbol', 'N/A')})")
                dpg.add_text(main_token.get("address", "N/A")[:22] + "...")
                dpg.add_text(entry.get("pair_address", "N/A")[:22] + "...")
                dpg.add_text(f"{entry.get('liquidity_eth', 0):.2f}")
                dpg.add_text("Yes" if entry.get("honeypot", False) else "No")
                dpg.add_text("Renounced" if entry.get("ownership_renounced", False) else "Not Renounced")
    except Exception as e:
        print(f"Error loading historical data: {e}")

def close_gui():
    dpg.destroy_context()

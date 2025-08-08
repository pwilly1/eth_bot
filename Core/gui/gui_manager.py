# gui_manager.py

import dearpygui.dearpygui as dpg

dpg.create_context()

def setup_gui():
    with dpg.window(label="UNISWAP Tracker", width=800, height=600):
        dpg.add_text("Status: 🔄 Starting...", tag="status")
        dpg.add_separator()

        with dpg.tab_bar():
            with dpg.tab(label="Token Events"):
                dpg.add_text("Detected Tokens:")
                dpg.add_child_window(height=200, tag="token_log_window")
            with dpg.tab(label="Wallet Alerts"):
                dpg.add_text("Wallet Activity:")
                dpg.add_child_window(height=200, tag="wallet_log_window")

    dpg.create_viewport(title='UNISWAP Tracker', width=800, height=600)
    dpg.setup_dearpygui()
    dpg.show_viewport()

def update_token_log(message: str):
    dpg.add_text(message, parent="token_log_window")

def update_wallet_log(message: str):
    dpg.add_text(message, parent="wallet_log_window")

def update_status(message: str):
    dpg.set_value("status", f"Status: {message}")

def render_gui():
    print("GUI thread started")
    while dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()


def close_gui():
    dpg.destroy_context()


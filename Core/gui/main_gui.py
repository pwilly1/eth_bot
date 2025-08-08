from dearpygui import dearpygui as dpg
import json
import os

LOG_FILE = "logs/tokens.json"
ROW_TAGS = []  # Track row tags for cleanup

def load_tokens():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def refresh_tokens():
    global ROW_TAGS

    # Delete only previous rows
    for tag in ROW_TAGS:
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)

    ROW_TAGS.clear()

    tokens = load_tokens()
    for i, t in enumerate(tokens):
        token0 = t.get("token0", {})
        token1 = t.get("token1", {})

        values = [
            str(token0.get("symbol", "N/A")),
            str(token1.get("symbol", "N/A")),
            str(t.get("honeypot", "N/A")),
            str(t.get("ownership_renounced", "N/A")),
            str(t.get("liquidity_eth", "N/A")),
            str(t.get("timestamp", "N/A"))
        ]

        row_tag = f"row_{i}"
        with dpg.table_row(parent="token_table", tag=row_tag):
            for v in values:
                dpg.add_text(v)
        ROW_TAGS.append(row_tag)

dpg.create_context()

with dpg.window(label="Token Log Viewer", width=920, height=540):
    dpg.add_button(label="Refresh Logs", callback=refresh_tokens)
    
    with dpg.table(tag="token_table", header_row=True, borders_innerH=True, borders_outerH=True, borders_innerV=True, borders_outerV=True):
        dpg.add_table_column(label="Token0")
        dpg.add_table_column(label="Token1")
        dpg.add_table_column(label="Honeypot")
        dpg.add_table_column(label="Renounced")
        dpg.add_table_column(label="Liquidity (ETH)")
        dpg.add_table_column(label="Timestamp")

dpg.create_viewport(title='Token Analyzer GUI', width=940, height=560)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.set_frame_callback(1, refresh_tokens)
dpg.start_dearpygui()
dpg.destroy_context()

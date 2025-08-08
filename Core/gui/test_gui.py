# test_gui.py

from gui_manager import setup_gui, render_gui, update_token_log, update_wallet_log, update_status
import threading, time

# 1. Launch the GUI
setup_gui()
threading.Thread(target=render_gui, daemon=True).start()
update_status("🟢 GUI Test Running")

# 2. Pump in some fake messages
for i in range(5):
    update_token_log(f"Test token event #{i}")
    update_wallet_log(f"Test wallet alert #{i}")
    time.sleep(1)

# 3. Keep it open for a few more seconds
time.sleep(5)

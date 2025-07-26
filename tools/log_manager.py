import os
import json
from datetime import datetime
import shutil

LOG_FILE = "logs/tokens.json"
BACKUP_DIR = "logs/backups"

def load_logs():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def count_entries():
    logs = load_logs()
    print(f"[📊] Total logged tokens: {len(logs)}")

def view_recent(n=5):
    logs = load_logs()
    if not logs:
        print("[⚠️] No logs found.")
        return
    print(f"[📄] Showing last {n} token logs:")
    for i, log in enumerate(logs[-n:], 1):
        print(f"{i}. {log['token0']['symbol']} / {log['token1']['symbol']} - WETH Pair: {log['is_weth_pair']} - Honeypot: {log['honeypot']}")

def clear_logs():
    open(LOG_FILE, "w").write("[]")
    print("[🧹] logs/tokens.json has been cleared.")

def backup_logs():
    logs = load_logs()
    if not logs:
        print("[⚠️] Nothing to backup.")
        return
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    backup_file = os.path.join(BACKUP_DIR, f"tokens-{timestamp}.json")
    shutil.copy(LOG_FILE, backup_file)
    print(f"[💾] Backup created at: {backup_file}")

def show_menu():
    while True:
        print("\n====== Meme Bot Log Manager ======")
        print("1. View log count")
        print("2. View recent logs")
        print("3. Clear logs")
        print("4. Backup logs")
        print("5. Exit")
        choice = input("Choose an option: ").strip()

        if choice == "1":
            count_entries()
        elif choice == "2":
            view_recent()
        elif choice == "3":
            clear_logs()
        elif choice == "4":
            backup_logs()
        elif choice == "5":
            print("Exiting log manager.")
            break
        else:
            print("Invalid option. Try again.")

if __name__ == "__main__":
    show_menu()

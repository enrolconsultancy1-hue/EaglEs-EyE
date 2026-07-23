from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from colorama import init, Fore
import time

init(autoreset=True)

print(Fore.GREEN + "=" * 50)
print(Fore.GREEN + "        EaglEs EyE v0.1")
print(Fore.GREEN + "        Watch. Mirror. Protect.")
print(Fore.GREEN + "=" * 50)

class EyeHandler(FileSystemEventHandler):

    def on_created(self, event):
        print(Fore.GREEN + f"[CREATED] {event.src_path}")

    def on_modified(self, event):
        print(Fore.YELLOW + f"[MODIFIED] {event.src_path}")

    def on_deleted(self, event):
        print(Fore.RED + f"[DELETED] {event.src_path}")

observer = Observer()

handler = EyeHandler()

observer.schedule(handler, ".", recursive=True)

observer.start()

print("\nWatching current folder...")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()

observer.join()
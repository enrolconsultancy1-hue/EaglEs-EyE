from core.event_bus import EventBus

bus = EventBus()


def logger(event):
    print("Logger received:", event)


def dashboard(event):
    print("Dashboard updated:", event)


bus.subscribe("FILE_CREATED", logger)
bus.subscribe("FILE_CREATED", dashboard)

bus.publish(
    "FILE_CREATED",
    {
        "file": "main.dart"
    }
)
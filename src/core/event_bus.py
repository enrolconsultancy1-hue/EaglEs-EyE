import itertools
from collections import defaultdict


class EventBus:
    def __init__(self):
        self._listeners = defaultdict(list)
        self._tokens = defaultdict(list)
        self._counter = itertools.count()

    def subscribe(self, event_name, callback):
        token = next(self._counter)
        self._listeners[event_name].append((token, callback))
        self._tokens[token].append(event_name)
        print("[EVENT BUS] SUBSCRIBED:", event_name, "TOTAL:", len(self._listeners[event_name]))
        return token

    def unsubscribe(self, token):
        event_names = self._tokens.pop(token, [])
        for event_name in event_names:
            self._listeners[event_name] = [
                (t, cb) for t, cb in self._listeners[event_name] if t != token
            ]

    def publish(self, event_name, data=None):
        subscribers = self._listeners.get(event_name, [])
        print("[EVENT BUS]", event_name, "SUBSCRIBERS:", len(subscribers))
        for token, callback in subscribers:
            try:
                callback(data)
            except Exception as e:
                print("[EVENT BUS] ERROR in", event_name, "subscriber:", e)

from collections import defaultdict


class EventBus:


    def __init__(
        self
    ):

        self._listeners = defaultdict(list)



    def subscribe(
        self,
        event_name,
        callback
    ):

        self._listeners[event_name].append(
            callback
        )


        print(
            "[EVENT BUS] SUBSCRIBED:",
            event_name,
            "TOTAL:",
            len(
                self._listeners[event_name]
            )
        )




    def publish(
        self,
        event_name,
        data=None
    ):


        subscribers = self._listeners.get(
            event_name,
            []
        )


        print(
            "[EVENT BUS]",
            event_name,
            "SUBSCRIBERS:",
            len(subscribers)
        )



        for callback in subscribers:

            callback(data)
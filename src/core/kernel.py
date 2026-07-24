from core.event_bus import EventBus



class EyeKernel:


    def __init__(self):

        self.event_bus = EventBus()

        self.services = {}

        self.config = {}



    def register_service(self, service):

        self.services[service.name] = service

        print(
            f"[KERNEL] Registered: {service.name}"
        )



    def get_service(self, name):

        return self.services.get(
            name
        )



    def set_config(self, config):

        self.config = config


        print(
            "[KERNEL] Configuration loaded."
        )



    def get_config(self):

        return self.config



    def start(self):

        print("\n===================================")

        print(
            "        EaglEs EyE Kernel"
        )

        print(
            "===================================\n"
        )


        for service in self.services.values():

            service.start()



        print(
            "\nKernel Ready.\n"
        )
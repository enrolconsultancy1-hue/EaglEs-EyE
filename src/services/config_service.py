import json
import os

from services.service import Service


class ConfigService(Service):


    def __init__(
        self,
        kernel,
        path="config/eye.config.json"
    ):

        super().__init__(kernel)

        self.path = path



    def start(self):

        super().start()

        self.load()



    def load(self):

        if not os.path.exists(self.path):

            print(
                "[CONFIG] Missing configuration."
            )

            return



        with open(
            self.path,
            "r"
        ) as file:

            config = json.load(file)



        self.kernel.set_config(
            config
        )


        print(
            "[CONFIG] Loaded:",
            self.path
        )
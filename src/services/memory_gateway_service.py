import os
import json

from services.service import Service



class MemoryGatewayService(Service):


    def __init__(
        self,
        kernel
    ):

        super().__init__(kernel)

        self.memory_path = None

        self.sources = {}




    def start(self):

        super().start()


        config = self.kernel.get_config()


        self.memory_path = config.get(
            "memory_path",
            "memory"
        )


        self.sources = {

            "semantic":
                os.path.join(
                    self.memory_path,
                    "knowledge.json"
                ),


            "vision":
                os.path.join(
                    self.memory_path,
                    "vision_memory.json"
                )

        }



        self.kernel.event_bus.subscribe(
            "IMAGE_OBSERVED",
            self.receive
        )


        print(
            "[MEMORY GATEWAY] Ready."
        )




    def stop(self):

        super().stop()




    def receive(
        self,
        data
    ):


        print(
            "[MEMORY GATEWAY] Received:",
            data.get(
                "filename"
            )
        )




    def recall(
        self,
        query
    ):


        results = []



        for name, path in self.sources.items():



            if not os.path.exists(
                path
            ):

                continue




            try:


                with open(
                    path,
                    "r",
                    encoding="utf-8"
                ) as f:


                    memory = json.load(
                        f
                    )




                for item in memory:



                    text = json.dumps(
                        item
                    ).lower()



                    if query.lower() in text:


                        results.append(

                            {
                                "source":
                                    name,

                                "memory":
                                    item

                            }

                        )



            except Exception:


                pass




        return results
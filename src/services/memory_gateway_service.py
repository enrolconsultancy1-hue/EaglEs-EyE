import os
import json

from datetime import datetime

from services.service import Service



class MemoryGatewayService(Service):


    def __init__(
        self,
        kernel
    ):

        super().__init__(kernel)

        self.memory_path = None

        self.sources = {}

        self.brain = None




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


        self.brain = self.kernel.services.get(
            "BrainService"
        )


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


        filename = data.get(
            "filename"
        )


        print(
            "[MEMORY GATEWAY] Received:",
            filename
        )



        if self.brain:


            self.brain.remember(

                "vision",

                json.dumps(
                    data
                )

            )


            print(
                "[MEMORY GATEWAY] Sent to Brain:",
                filename
            )


        else:


            print(
                "[MEMORY GATEWAY] Brain unavailable."
            )




    def search(
        self,
        query
    ):

        results = []


        for source, path in self.sources.items():


            if not os.path.exists(path):

                continue



            try:

                with open(
                    path,
                    "r",
                    encoding="utf-8"
                ) as f:

                    memories = json.load(f)



                for memory in memories:


                    text = json.dumps(
                        memory
                    ).lower()


                    score = 0



                    if query.lower() in text:

                        score += 1



                    if query.lower() in str(
                        memory.get(
                            "filename",
                            ""
                        )
                    ).lower():

                        score += 2



                    if score > 0:


                        results.append(

                            {
                                "source": source,

                                "score": score,

                                "timestamp":
                                    datetime.now().isoformat(),

                                "memory": memory
                            }

                        )



            except Exception:

                pass



        results.sort(
            key=lambda x: x["score"],
            reverse=True
        )


        return results




    def recall(
        self,
        query
    ):


        if self.brain:


            brain_results = self.brain.recall(
                query
            )


            if brain_results:

                return brain_results



        return self.search(
            query
        )
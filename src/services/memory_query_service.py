import os
import json

from services.service import Service


class MemoryQueryService(Service):

    def __init__(self, kernel):

        super().__init__(kernel)

        self.memory_path = None

        self.knowledge_file = None



    def start(self):

        super().start()

        config = self.kernel.get_config()

        self.memory_path = config.get(
            "memory_path",
            "memory"
        )


        self.knowledge_file = os.path.join(
            self.memory_path,
            "knowledge.json"
        )


        print(
            "[MEMORY QUERY] Ready."
        )



    def search(
        self,
        query,
        category=None
    ):


        knowledge = self._load()


        results = []


        query = query.lower()



        for path, item in knowledge.items():


            content = item.get(
                "content",
                ""
            )


            if content is None:

                continue



            if category:


                if item.get(
                    "category"
                ) != category:

                    continue



            searchable = (

                item.get(
                    "filename",
                    ""
                )

                + " "

                + content

            ).lower()



            if query in searchable:


                results.append(

                    {

                        "file":
                            item.get(
                                "filename"
                            ),


                        "category":
                            item.get(
                                "category"
                            ),


                        "content":
                            content,


                        "path":
                            path

                    }

                )



        return results




    def _load(self):


        try:

            with open(

                self.knowledge_file,

                "r",

                encoding="utf-8"

            ) as f:


                return json.load(f)



        except Exception:


            return {}



    def stop(self):

        super().stop()
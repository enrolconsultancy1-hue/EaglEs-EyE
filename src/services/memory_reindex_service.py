import os
import json

from services.service import Service


class MemoryReindexService(Service):

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
            "[REINDEX] Ready."
        )



    def detect_category(self, item):

        file_type = item.get(
            "type",
            ""
        )


        if file_type == "configuration":

            return "configuration"



        if file_type in [

            "python_source",
            "javascript_source"

        ]:

            return "code"



        if file_type in [

            "text_document",
            "markdown"

        ]:

            return "knowledge"



        if file_type in [

            "image",
            "audio",
            "video"

        ]:

            return "media"



        return "unknown"




    def reindex(self):

        knowledge = self._load()


        updated = 0



        for path, item in knowledge.items():


            if "category" not in item:


                item["category"] = self.detect_category(
                    item
                )

                updated += 1




            if item.get("content") is None:


                if os.path.exists(path):

                    try:

                        with open(
                            path,
                            "r",
                            encoding="utf-8"
                        ) as f:


                            item["content"] = f.read()

                            updated += 1


                    except Exception:

                        pass




        self._save(
            knowledge
        )


        print(
            "[REINDEX] Updated:",
            updated
        )




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




    def _save(self, data):

        with open(
            self.knowledge_file,
            "w",
            encoding="utf-8"
        ) as f:


            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

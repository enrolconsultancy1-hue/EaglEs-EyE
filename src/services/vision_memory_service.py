import os
import json
import hashlib

from datetime import datetime

from services.service import Service



class VisionMemoryService(Service):


    def __init__(
        self,
        kernel
    ):

        super().__init__(kernel)

        self.memory_path = None

        self.vision_file = None



    def start(self):

        super().start()


        config = self.kernel.get_config()


        self.memory_path = config.get(
            "memory_path",
            "memory"
        )


        self.vision_file = os.path.join(
            self.memory_path,
            "vision_memory.json"
        )


        os.makedirs(
            self.memory_path,
            exist_ok=True
        )


        if not os.path.exists(
            self.vision_file
        ):

            self._create_memory()



        self.kernel.event_bus.subscribe(
            "IMAGE_OBSERVED",
            self.remember
        )


        print(
            "[VISION MEMORY] Ready."
        )




    def stop(self):

        super().stop()




    def sha256(
        self,
        path
    ):

        try:

            h = hashlib.sha256()


            with open(
                path,
                "rb"
            ) as f:


                while True:

                    chunk = f.read(8192)


                    if not chunk:

                        break


                    h.update(
                        chunk
                    )


            return h.hexdigest()


        except Exception:

            return None





    def remember(
        self,
        data
    ):


        memories = self._load()


        path = data.get(
            "path"
        )


        file_hash = self.sha256(
            path
        )



        now = datetime.now().isoformat()



        # Check existing visual memory

        for memory in memories:


            if memory.get(
                "sha256"
            ) == file_hash:


                memory["last_seen"] = now

                memory["observations"] = (
                    memory.get(
                        "observations",
                        1
                    ) + 1
                )


                self._save(
                    memories
                )


                print(
                    "[VISION MEMORY] Updated:",
                    memory["filename"]
                )


                return




        # New visual memory

        observation = {


            "filename":
                data.get(
                    "filename"
                ),


            "path":
                path,


            "category":
                data.get(
                    "category",
                    "visual_memory"
                ),


            "type":
                "image",


            "width":
                data.get(
                    "width"
                ),


            "height":
                data.get(
                    "height"
                ),


            "format":
                data.get(
                    "format"
                ),


            "sha256":
                file_hash,


            "first_seen":
                now,


            "last_seen":
                now,


            "observations":
                1

        }



        memories.append(
            observation
        )


        self._save(
            memories
        )


        print(
            "[VISION MEMORY] Stored:",
            observation["filename"]
        )





    def _save(
        self,
        memories
    ):


        with open(
            self.vision_file,
            "w",
            encoding="utf-8"
        ) as f:


            json.dump(
                memories,
                f,
                indent=4,
                ensure_ascii=False
            )





    def _create_memory(
        self
    ):


        self._save(
            []
        )




    def _load(
        self
    ):


        try:

            with open(
                self.vision_file,
                "r",
                encoding="utf-8"
            ) as f:


                return json.load(f)



        except Exception:

            return []
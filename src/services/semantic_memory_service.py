import os
import json
import mimetypes
import hashlib

from datetime import datetime

from services.service import Service


class SemanticMemoryService(Service):

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

        os.makedirs(
            self.memory_path,
            exist_ok=True
        )

        if not os.path.exists(
            self.knowledge_file
        ):
            self._create_knowledge()


        self.kernel.event_bus.subscribe(
            "FILE_CREATED",
            self.learn
        )

        self.kernel.event_bus.subscribe(
            "FILE_MODIFIED",
            self.learn
        )

        self.kernel.event_bus.subscribe(
            "FILE_DELETED",
            self.learn
        )


    def stop(self):

        super().stop()



    def detect_type(self, extension, mime):

        extension = extension.lower()


        if extension == ".txt":
            return "text_document"


        if extension == ".md":
            return "markdown"


        if extension == ".py":
            return "python_source"


        if extension == ".js":
            return "javascript_source"


        if extension == ".json":
            return "configuration"


        if extension in [
            ".yaml",
            ".yml"
        ]:
            return "configuration"


        if extension in [
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
            ".webp"
        ]:
            return "image"


        if extension == ".pdf":
            return "pdf_document"


        if mime:

            if mime.startswith("text/"):
                return "text_document"


            if mime.startswith("image/"):
                return "image"


        return "unknown"



    def detect_category(self, extension, file_type):


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




    def sha256(self, path):

        h = hashlib.sha256()


        try:

            with open(
                path,
                "rb"
            ) as f:


                while True:


                    chunk = f.read(8192)


                    if not chunk:
                        break


                    h.update(chunk)


            return h.hexdigest()



        except Exception:

            return None




    def read_content(self, path):

        supported = [

            ".txt",
            ".md",
            ".py",
            ".json",
            ".yaml",
            ".yml"

        ]


        extension = os.path.splitext(path)[1].lower()


        if extension not in supported:

            return None



        try:

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as f:

                return f.read()



        except Exception:

            return None




    def learn(self, data):

        path = data.get(
            "path",
            ""
        )


        path_lower = path.lower()



        if "mirror" in path_lower:

            return



        if "memory" in path_lower:

            return




        knowledge = self._load()


        now = datetime.now().isoformat()



        extension = os.path.splitext(path)[1].lower()


        mime, _ = mimetypes.guess_type(path)


        file_type = self.detect_type(
            extension,
            mime
        )


        category = self.detect_category(
            extension,
            file_type
        )



        if path in knowledge:



            knowledge[path]["last_seen"] = now

            knowledge[path]["observations"] += 1

            knowledge[path]["sha256"] = self.sha256(path)

            knowledge[path]["content"] = self.read_content(path)

            knowledge[path]["category"] = category




        else:



            try:

                size = os.stat(path).st_size


            except Exception:

                size = 0




            knowledge[path] = {


                "filename":
                    os.path.basename(path),


                "category":
                    category,


                "extension":
                    extension,


                "type":
                    file_type,


                "mime":
                    mime,


                "size":
                    size,


                "sha256":
                    self.sha256(path),


                "content":
                    self.read_content(path),


                "folder":
                    os.path.dirname(path),


                "first_seen":
                    now,


                "last_seen":
                    now,


                "observations":
                    1,


                "status":
                    "active"

            }




        with open(
            self.knowledge_file,
            "w",
            encoding="utf-8"
        ) as f:


            json.dump(
                knowledge,
                f,
                indent=4,
                ensure_ascii=False
            )



        print(
            "[SEMANTIC] Learned:",
            os.path.basename(path)
        )




    def _create_knowledge(self):

        with open(
            self.knowledge_file,
            "w",
            encoding="utf-8"
        ) as f:


            json.dump(
                {},
                f,
                indent=4
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
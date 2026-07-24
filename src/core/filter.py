import os


class EyeFilter:


    def __init__(
        self,
        ignored=None
    ):

        self.ignored = ignored or []



    def allowed(
        self,
        path
    ):

        path = os.path.abspath(
            path
        )


        normalized = path.lower()



        parts = normalized.split(
            os.sep
        )



        for item in self.ignored:


            item = item.lower()



            if item in parts:

                return False



        filename = os.path.basename(
            normalized
        )



        # Ignore hidden files

        if filename.startswith("."):

            return False



        # Ignore temporary files

        temp_extensions = [

            ".tmp",
            ".temp",
            ".bak",
            ".swp"

        ]


        for ext in temp_extensions:

            if filename.endswith(ext):

                return False



        return True
import os

from datetime import datetime

from PIL import Image

from services.service import Service



class VisionService(Service):


    def __init__(
        self,
        kernel
    ):

        super().__init__(
            kernel
        )


        self.supported = [

            ".png",
            ".jpg",
            ".jpeg",
            ".bmp",
            ".webp",
            ".gif"

        ]



    def start(self):

        super().start()



        self.kernel.event_bus.subscribe(
            "FILE_CREATED",
            self.observe
        )


        self.kernel.event_bus.subscribe(
            "FILE_MODIFIED",
            self.observe
        )



        print(
            "[VISION] Ready."
        )



    def stop(self):

        super().stop()





    def observe(
        self,
        data
    ):


        path = data.get(
            "path",
            ""
        )



        extension = os.path.splitext(
            path
        )[1].lower()



        if extension not in self.supported:

            return




        vision = self.analyze_image(
            path
        )



        if vision:


            print(
                "[VISION] Observed:",
                os.path.basename(path)
            )


            print(
                vision
            )



            self.kernel.event_bus.publish(

                "IMAGE_OBSERVED",

                vision

            )







    def analyze_image(
        self,
        path
    ):


        try:


            image = Image.open(
                path
            )


            width, height = image.size



            return {


                "filename":

                    os.path.basename(path),



                "path":

                    path,



                "category":

                    "visual_memory",



                "type":

                    "image",



                "width":

                    width,



                "height":

                    height,



                "format":

                    image.format,



                "observed":

                    datetime.now().isoformat()


            }



        except Exception:


            return None
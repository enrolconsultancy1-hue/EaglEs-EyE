import os


class EyeFilter:


    def __init__(self, ignored=None):

        self.ignored = ignored or []



    def allowed(self, path):

        path = os.path.abspath(path)


        for item in self.ignored:

            if item.lower() in path.lower():

                return False


        return True
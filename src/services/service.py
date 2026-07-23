class Service:
    def __init__(self, kernel):
        self.kernel = kernel
        self.name = self.__class__.__name__

    def start(self):
        print(f"[SERVICE] {self.name} started.")

    def stop(self):
        print(f"[SERVICE] {self.name} stopped.")
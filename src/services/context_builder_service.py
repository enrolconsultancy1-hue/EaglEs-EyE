from services.service import Service


class ContextBuilderService(Service):


    def __init__(self, kernel):

        super().__init__(kernel)

        self.memory_query = None



    def start(self):

        super().start()


        self.memory_query = (
            self.kernel.get_service(
                "MemoryQueryService"
            )
        )


        print(
            "[CONTEXT BUILDER] Ready."
        )



    def build(
        self,
        question
    ):


        if not self.memory_query:

            return ""


        memories = self.memory_query.search(
            question,
            category="knowledge"
        )


        if not memories:

            return (
                "No relevant memory found."
            )



        context = []


        for item in memories:


            context.append(

                "SOURCE: "
                + item["file"]
                + "\n\n"
                + item["content"]

            )


        return "\n\n---\n\n".join(
            context
        )



    def stop(self):

        super().stop()

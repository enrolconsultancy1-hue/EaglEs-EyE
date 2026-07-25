from services.service import Service


class ContextBuilderService(Service):


    def __init__(self, kernel):

        super().__init__(kernel)

        self.memory_query = None
        self.retrieval = None



    def start(self):

        super().start()


        self.memory_query = (
            self.kernel.get_service(
                "MemoryQueryService"
            )
        )
        self.retrieval = self.kernel.get_service("RetrievalService")


        print(
            "[CONTEXT BUILDER] Ready."
        )



    def build(
        self,
        question
    ):


        if not self.memory_query:

            return ""


        if self.retrieval:
            return self.build_rag_context(question)

        memories = self.memory_query.search(question, category="knowledge")


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

    def build_rag_context(self, question, max_chars=6000, limit=12):
        """Build compact, cited context without blindly concatenating files."""
        results = self.retrieval.search(question, limit=limit)
        if not results:
            return "No relevant memory found."
        sections = []
        seen = set()
        used = 0
        for item in results:
            identity = (item["path"], item["offset"])
            if identity in seen:
                continue
            seen.add(identity)
            excerpt = item["content"].strip()
            if not excerpt:
                continue
            remaining = max_chars - used
            if remaining <= 0:
                break
            excerpt = excerpt[:remaining]
            section = "Source: {0}\nCitation: {1}\n\nRelevant:\n{2}".format(
                item["filename"], item["citation"], excerpt
            )
            sections.append(section)
            used += len(excerpt)
        return "\n\n---\n\n".join(sections) or "No relevant memory found."



    def stop(self):

        super().stop()

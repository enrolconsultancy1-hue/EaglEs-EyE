import os
import sqlite3

from datetime import datetime

from services.service import Service


class BrainService(Service):


    def __init__(
        self,
        kernel
    ):

        super().__init__(kernel)

        self.memory_path = None

        self.database = None

        self.connection = None



    def start(self):

        super().start()

        config = self.kernel.get_config()

        self.memory_path = config.get(
            "memory_path",
            "memory"
        )

        os.makedirs(
            self.memory_path,
            exist_ok=True
        )

        self.database = os.path.join(
            self.memory_path,
            "brain.db"
        )

        self.connection = sqlite3.connect(
            self.database,
            check_same_thread=False
        )

        self.connection.execute(

            """

            CREATE TABLE IF NOT EXISTS events (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                event_type TEXT,

                path TEXT,

                timestamp TEXT

            )

            """

        )

        self.connection.commit()



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

        self.kernel.event_bus.subscribe(
            "IMAGE_OBSERVED",
            self.learn
        )

        self.kernel.event_bus.subscribe(
            "SEMANTIC_LEARNED",
            self.learn
        )

        self.kernel.event_bus.subscribe(
            "VISION_MEMORY_STORED",
            self.learn
        )


        print(
            "[BRAIN] Ready."
        )



    def stop(self):

        if self.connection:

            self.connection.close()

        super().stop()



    def learn(
        self,
        data
    ):

        event_type = data.get(
            "event_type",
            "UNKNOWN"
        )

        path = data.get(
            "path",
            ""
        )


        self.connection.execute(

            """

            INSERT INTO events (

                event_type,

                path,

                timestamp

            )

            VALUES (

                ?, ?, ?

            )

            """,

            (

                event_type,

                path,

                datetime.now().isoformat()

            )

        )

        self.connection.commit()


        print(
            "[BRAIN] Learned:",
            event_type
        )



    def recent(
        self,
        limit=10
    ):

        cursor = self.connection.execute(

            """

            SELECT

                event_type,

                path,

                timestamp

            FROM events

            ORDER BY id DESC

            LIMIT ?

            """,

            (

                limit,

            )

        )

        return cursor.fetchall()



    def search(
        self,
        keyword
    ):

        cursor = self.connection.execute(

            """

            SELECT

                event_type,

                path,

                timestamp

            FROM events

            WHERE path LIKE ?

            ORDER BY id DESC

            """,

            (

                "%" + keyword + "%",

            )

        )

        return cursor.fetchall()



    def remember(
        self,
        path
    ):

        cursor = self.connection.execute(

            """

            SELECT

                event_type,

                path,

                timestamp

            FROM events

            WHERE path=?

            ORDER BY id DESC

            LIMIT 1

            """,

            (

                path,

            )

        )

        return cursor.fetchone()



    def statistics(
        self
    ):

        cursor = self.connection.execute(

            """

            SELECT COUNT(*)

            FROM events

            """

        )

        return cursor.fetchone()[0]



    def consolidate(
        self
    ):

        sources = [

            "knowledge.json",

            "vision_memory.json",

            "memory.json"

        ]


        total = 0


        for source in sources:


            path = os.path.join(

                self.memory_path,

                source

            )


            if not os.path.exists(path):

                continue



            self.connection.execute(

                """

                INSERT INTO events (

                    event_type,

                    path,

                    timestamp

                )

                VALUES (

                    ?, ?, ?

                )

                """,

                (

                    "CONSOLIDATED",

                    source,

                    datetime.now().isoformat()

                )

            )


            total += 1



        self.connection.commit()


        print(
            "[BRAIN] Consolidated:",
            total
        )
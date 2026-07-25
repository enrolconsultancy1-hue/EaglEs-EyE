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

            CREATE TABLE IF NOT EXISTS memories (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                source TEXT,

                content TEXT,

                timestamp TEXT

            )

            """

        )


        self.connection.commit()


        print(
            "[BRAIN] Ready."
        )




    def stop(self):

        if self.connection:

            self.connection.close()


        super().stop()




    def remember(
        self,
        source,
        content
    ):


        self.connection.execute(

            """

            INSERT INTO memories

            (

                source,

                content,

                timestamp

            )

            VALUES

            (?, ?, ?)

            """,

            (

                source,

                content,

                datetime.now().isoformat()

            )

        )


        self.connection.commit()



    def recall(
        self,
        query
    ):


        cursor = self.connection.execute(

            """

            SELECT

                source,

                content,

                timestamp

            FROM memories

            WHERE content LIKE ?

            ORDER BY id DESC

            """,

            (

                "%" + query + "%",

            )

        )


        return cursor.fetchall()




    def statistics(
        self
    ):


        cursor = self.connection.execute(

            """

            SELECT COUNT(*)

            FROM memories

            """

        )


        return cursor.fetchone()[0]




    def recent(
        self,
        limit=10
    ):


        cursor = self.connection.execute(

            """

            SELECT

                source,

                content,

                timestamp

            FROM memories

            ORDER BY id DESC

            LIMIT ?

            """,

            (

                limit,

            )

        )


        return cursor.fetchall()
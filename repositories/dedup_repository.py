import sqlite3
from datetime import datetime


class DedupRepository:

    def __init__(self, db_path="rca.db"):

        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False
        )

        self.create_table()

    # ----------------------------------------------------

    def create_table(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_problems(

            problem_key TEXT PRIMARY KEY,

            original_problem_id TEXT,

            incident_number TEXT,

            host TEXT,

            problem TEXT,

            first_seen TEXT,

            last_seen TEXT,

            occurrences INTEGER,

            status TEXT
        )
        """)

        self.conn.commit()

    # ----------------------------------------------------

    def build_key(self, host, problem):

        return f"{host}|{problem}".lower()

    # ----------------------------------------------------

    def find(self, host, problem):

        key = self.build_key(host, problem)

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT
            problem_key,
            original_problem_id,
            incident_number,
            occurrences,
            status

        FROM active_problems

        WHERE problem_key=?

        """, (key,))

        return cursor.fetchone()

    # ----------------------------------------------------

    def create(

        self,

        original_problem_id,

        incident_number,

        host,

        problem

    ):

        key = self.build_key(host, problem)

        now = datetime.utcnow().isoformat()

        cursor = self.conn.cursor()

        cursor.execute("""

        INSERT OR REPLACE INTO active_problems(

            problem_key,

            original_problem_id,

            incident_number,

            host,

            problem,

            first_seen,

            last_seen,

            occurrences,

            status

        )

        VALUES(?,?,?,?,?,?,?,?,?)

        """,(

            key,

            original_problem_id,

            incident_number,

            host,

            problem,

            now,

            now,

            1,

            "OPEN"

        ))

        self.conn.commit()

    # ----------------------------------------------------

    def increment(self, host, problem):

        key = self.build_key(host, problem)

        cursor = self.conn.cursor()

        cursor.execute("""

        UPDATE active_problems

        SET

            occurrences = occurrences + 1,

            last_seen = ?

        WHERE problem_key=?

        """,(

            datetime.utcnow().isoformat(),

            key

        ))

        self.conn.commit()

    # ----------------------------------------------------

    def resolve(self, host, problem):

        key = self.build_key(host, problem)

        cursor = self.conn.cursor()

        cursor.execute("""

        UPDATE active_problems

        SET status='RESOLVED'

        WHERE problem_key=?

        """,(key,))

        self.conn.commit()
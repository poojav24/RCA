import sqlite3
import json
from datetime import datetime


class RCARepository:

    def __init__(self, db_path="rca.db"):

        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False
        )

        self.create_table()

    def create_table(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rca_results(

            problem_id TEXT PRIMARY KEY,

            incident_number TEXT,

            host TEXT,

            problem TEXT,

            root_cause TEXT,

            confidence REAL,

            impact TEXT,

            reasoning TEXT,

            resolution TEXT,

            diagnostics TEXT,

            created_at TEXT

        )
        """)

        self.conn.commit()

    # ----------------------------------------------------

    def save(self, problem_id, incident, parsed_alert, rca):

        cursor = self.conn.cursor()

        cursor.execute("""

        INSERT OR REPLACE INTO rca_results(

            problem_id,
            incident_number,
            host,
            problem,
            root_cause,
            confidence,
            impact,
            reasoning,
            resolution,
            diagnostics,
            created_at

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?)

        """, (

            problem_id,

            incident.snow.get("number")
            if incident.snow else None,

            parsed_alert.host,

            parsed_alert.problem,

            rca.get("root_cause"),

            rca.get("confidence"),

            rca.get("impact"),

            json.dumps(
                rca.get("reasoning", [])
            ),

            json.dumps(
                rca.get("recommended_resolution", [])
            ),

            json.dumps(
                rca.get("next_diagnostics", [])
            ),

            datetime.utcnow().isoformat()

        ))

        self.conn.commit()

    # ----------------------------------------------------

    def get(self, problem_id):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT *

        FROM rca_results

        WHERE problem_id=?

        """, (problem_id,))

        row = cursor.fetchone()

        if row is None:
            return None

        return {

            "problem_id": row[0],

            "incident_number": row[1],

            "host": row[2],

            "problem": row[3],

            "root_cause": row[4],

            "confidence": row[5],

            "impact": row[6],

            "reasoning": json.loads(row[7]),

            "recommended_resolution": json.loads(row[8]),

            "next_diagnostics": json.loads(row[9]),

            "created_at": row[10]

        }

    def get_by_host_problem(self, host, problem):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT *
        FROM rca_results
        WHERE host=? AND problem=?
        ORDER BY created_at DESC
        LIMIT 1
        """,(
            host,
            problem
        ))

        row = cursor.fetchone()

        if row is None:
            return None

        return {

            "problem_id": row[0],
            "incident_number": row[1],
            "host": row[2],
            "problem": row[3],
            "root_cause": row[4],
            "confidence": row[5],
            "impact": row[6],
            "reasoning": json.loads(row[7]),
            "recommended_resolution": json.loads(row[8]),
            "next_diagnostics": json.loads(row[9]),
            "created_at": row[10]

        }
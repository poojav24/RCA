import sqlite3
import json
from datetime import datetime


class KnowledgeRepository:

    def __init__(self, db_path="rca.db"):

        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False
        )

        self.create_table()

    # -----------------------------------------------------

    def create_table(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_base(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            problem_id TEXT,

            trigger_id TEXT,

            incident_number TEXT,

            host TEXT,

            problem TEXT,

            severity TEXT,

            technology TEXT,

            metrics TEXT,

            log_summary TEXT,

            root_cause TEXT,

            confidence REAL,

            impact TEXT,

            reasoning TEXT,

            remediation TEXT,

            diagnostics TEXT,

            created_at TEXT

        )
        """)

        # -----------------------------------------------------
        # Add trigger_id if upgrading an old database
        # -----------------------------------------------------

        cursor.execute("PRAGMA table_info(knowledge_base)")
        columns = [row[1] for row in cursor.fetchall()]

        if "trigger_id" not in columns:
            cursor.execute("""
                ALTER TABLE knowledge_base
                ADD COLUMN trigger_id TEXT
            """)

        # -----------------------------------------------------
        # Remove duplicate rows
        # -----------------------------------------------------

        cursor.execute("""
        DELETE FROM knowledge_base
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM knowledge_base
            GROUP BY host, problem
        )
        """)

        cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_host_problem
        ON knowledge_base(host, problem)
        """)

        self.conn.commit()

    # -----------------------------------------------------

    def exists(self, host, problem):

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT id
            FROM knowledge_base
            WHERE host=?
            AND problem=?
            LIMIT 1
            """,
            (
                host,
                problem
            )
        )

        row = cursor.fetchone()

        if row:
            return row[0]

        return None

    # -----------------------------------------------------

    def save(

        self,

        parsed_alert,

        incident,

        trigger,

        playbook,

        metrics,

        log_summary,

        rca

    ):

        cursor = self.conn.cursor()

        metric_list = []

        for metric in metrics:

            metric_list.append({

                "name": getattr(metric, "name", None),

                "key": getattr(metric, "key", None),

                "value": getattr(metric, "lastvalue", None),

                "unit": getattr(metric, "units", None),

                "status": getattr(metric, "status", None)

            })

        if isinstance(log_summary, (dict, list)):
            log_summary = json.dumps(log_summary)
        elif log_summary is not None:
            log_summary = str(log_summary)

        root_cause = rca.get("root_cause")

        if isinstance(root_cause, (dict, list)):
            root_cause = json.dumps(root_cause)

        impact = rca.get("impact")

        if isinstance(impact, (dict, list)):
            impact = json.dumps(impact)

        confidence = rca.get("confidence")

        reasoning = json.dumps(
            rca.get("reasoning", [])
        )

        remediation = json.dumps(
            rca.get("recommended_resolution", [])
        )

        diagnostics = json.dumps(
            rca.get("next_diagnostics", [])
        )

        technology = playbook.get("technology")

        existing_id = self.exists(

            parsed_alert.host,

            parsed_alert.problem

        )


        # =====================================================
        # UPDATE
        # =====================================================

        # =====================================================
        # UPDATE
        # =====================================================

        if existing_id:

            cursor.execute("""

            UPDATE knowledge_base

            SET

                problem_id=?,

                trigger_id=?,

                incident_number=?,

                severity=?,

                technology=?,

                metrics=?,

                log_summary=?,

                root_cause=?,

                confidence=?,

                impact=?,

                reasoning=?,

                remediation=?,

                diagnostics=?,

                created_at=?

            WHERE id=?

            """, (

                parsed_alert.original_problem_id,

                str(trigger.triggerid),

                incident.snow.get("number")
                if incident.snow else None,

                parsed_alert.severity,

                technology,

                json.dumps(metric_list),

                log_summary,

                root_cause,

                confidence,

                impact,

                reasoning,

                remediation,

                diagnostics,

                datetime.utcnow().isoformat(),

                existing_id

            ))

            print(
                "Knowledge Base Updated (Existing Incident)"
            )

        # =====================================================
        # INSERT
        # =====================================================

        else:

            cursor.execute("""

            INSERT INTO knowledge_base(

                problem_id,

                trigger_id,

                incident_number,

                host,

                problem,

                severity,

                technology,

                metrics,

                log_summary,

                root_cause,

                confidence,

                impact,

                reasoning,

                remediation,

                diagnostics,

                created_at

            )

            VALUES(
                ?,?,?,?,?,?,
                ?,?,?,?,?,?,
                ?,?,?,?
            )

            """, (

                parsed_alert.original_problem_id,

                str(trigger.triggerid),

                incident.snow.get("number")
                if incident.snow else None,

                parsed_alert.host,

                parsed_alert.problem,

                parsed_alert.severity,

                technology,

                json.dumps(metric_list),

                log_summary,

                root_cause,

                confidence,

                impact,

                reasoning,

                remediation,

                diagnostics,

                datetime.utcnow().isoformat()

            ))

            print(
                "Knowledge Base Inserted (New Incident)"
            )

        self.conn.commit()
    #---------------------------------------------------

    # -----------------------------------------------------

    # -----------------------------------------------------

    def search(self, host, problem):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT *

        FROM knowledge_base

        WHERE host = ?
           OR problem LIKE ?

        ORDER BY created_at DESC

        LIMIT 5

        """, (

            host,

            f"%{problem}%"

        ))

        rows = cursor.fetchall()

        results = []

        for row in rows:

            try:
                metrics = json.loads(row[8]) if row[8] else []
            except Exception:
                metrics = []

            try:
                reasoning = json.loads(row[13]) if row[13] else []
            except Exception:
                reasoning = []

            try:
                remediation = json.loads(row[14]) if row[14] else []
            except Exception:
                remediation = []

            try:
                diagnostics = json.loads(row[15]) if row[15] else []
            except Exception:
                diagnostics = []

            results.append({

                "problem_id": row[1],

                "trigger_id": row[2],

                "incident_number": row[3],

                "host": row[4],

                "problem": row[5],

                "severity": row[6],

                "technology": row[7],

                "metrics": metrics,

                "log_summary": row[9],

                "root_cause": row[10],

                "confidence": row[11],

                "impact": row[12],

                "reasoning": reasoning,

                "recommended_resolution": remediation,

                "next_diagnostics": diagnostics,

                "created_at": row[16]

            })

        return results

    # -----------------------------------------------------

    def get_all(self):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT *

        FROM knowledge_base

        ORDER BY created_at DESC

        """)

        rows = cursor.fetchall()

        incidents = []

        for row in rows:

            try:
                metrics = json.loads(row[8]) if row[8] else []
            except Exception:
                metrics = []

            try:
                reasoning = json.loads(row[13]) if row[13] else []
            except Exception:
                reasoning = []

            try:
                remediation = json.loads(row[14]) if row[14] else []
            except Exception:
                remediation = []

            try:
                diagnostics = json.loads(row[15]) if row[15] else []
            except Exception:
                diagnostics = []

            incidents.append({

                "id": row[0],

                "problem_id": row[1],

                "trigger_id": row[2],

                "incident_number": row[3],

                "host": row[4],

                "problem": row[5],

                "severity": row[6],

                "technology": row[7],

                "metrics": metrics,

                "log_summary": row[9],

                "root_cause": row[10],

                "confidence": row[11],

                "impact": row[12],

                "reasoning": reasoning,

                "recommended_resolution": remediation,

                "next_diagnostics": diagnostics,

                "created_at": row[16]

            })

        return incidents

    # -----------------------------------------------------

    def find_by_trigger(self, trigger_id):

        cursor = self.conn.cursor()

        cursor.execute("""

            SELECT *

            FROM knowledge_base

            WHERE trigger_id = ?

            ORDER BY id DESC

            LIMIT 1

        """, (str(trigger_id),))

        row = cursor.fetchone()

        if row is None:
            return None

        return {

            "id": row[0],
            "problem_id": row[1],
            "trigger_id": row[2],
            "incident_number": row[3],
            "host": row[4],
            "problem": row[5],
            "severity": row[6],
            "technology": row[7],
            "metrics": json.loads(row[8]) if row[8] else [],
            "log_summary": row[9],
            "root_cause": row[10],
            "confidence": row[11],
            "impact": row[12],
            "reasoning": json.loads(row[13]) if row[13] else [],
            "recommended_resolution": json.loads(row[14]) if row[14] else [],
            "next_diagnostics": json.loads(row[15]) if row[15] else [],
            "created_at": row[16]
        }
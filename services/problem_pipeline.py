from utils.pipeline_logger import PipelineLogger

class ProblemPipeline:

    def __init__(

        self,

        correlation_service,

        trigger_service,

        playbook_service,

        metric_service,

        log_fetcher,

        log_processor,

        log_summarizer,

        evidence_builder,

        rca_service,

        repository,

        dedup_repository

    ):

        self.correlation_service = correlation_service
        self.trigger_service = trigger_service
        self.playbook_service = playbook_service
        self.metric_service = metric_service

        self.log_fetcher = log_fetcher
        self.log_processor = log_processor
        self.log_summarizer = log_summarizer

        self.evidence_builder = evidence_builder
        self.rca_service = rca_service

        self.repository = repository

        self.dedup_repository = dedup_repository
    # ======================================================
    # Execute Problem Pipeline
    # ======================================================

    def run(self, parsed):

        existing = self.dedup_repository.find(

            parsed.host,

            parsed.problem

        )

        if existing and existing[4] == "OPEN":

            print()
            print("=" * 60)
            print("DUPLICATE ALERT DETECTED")
            print("=" * 60)

            self.dedup_repository.increment(

                parsed.host,

                parsed.problem

            )

            latest = self.dedup_repository.find(

                parsed.host,

                parsed.problem

            )

            print("Occurrences :", latest[3])

            print("Skipping RCA because this problem is already under analysis.")

            return
        PipelineLogger.header("PROCESSING PROBLEM ALERT")
        
        PipelineLogger.key_value("Alert ID", parsed.alertid)
        PipelineLogger.key_value("Host", parsed.host)
        PipelineLogger.key_value("Problem", parsed.problem)
        PipelineLogger.key_value("Severity", parsed.severity)
        PipelineLogger.key_value("Started At", parsed.started_time)
        PipelineLogger.key_value("Problem ID", parsed.original_problem_id)

        # ==========================================================
        # STEP 1 - ServiceNow Correlation
        # ==========================================================

        PipelineLogger.header("STEP 1 : SERVICENOW CORRELATION")

        incident = self.correlation_service.correlate(parsed)

        if incident.snow:

            snow = incident.snow

            PipelineLogger.success("Matching Incident Found")

            PipelineLogger.key_value("Incident", snow.get("number"))
            PipelineLogger.key_value("Priority", snow.get("priority"))
            PipelineLogger.key_value("Severity", snow.get("severity"))
            PipelineLogger.key_value("State", snow.get("state"))
            PipelineLogger.key_value("Assignment Group", snow.get("assignment_group"))

        else:

            PipelineLogger.warning("No matching ServiceNow Incident")

        # ==========================================================
        # STEP 2 - Knowledge Base Search
        # ==========================================================

        PipelineLogger.header("STEP 2 : KNOWLEDGE BASE SEARCH")

        PipelineLogger.info("Searching previous RCA...")

        previous_rca = self.repository.get(parsed.original_problem_id)

        if previous_rca:

            PipelineLogger.success("Previous RCA Found")

            PipelineLogger.key_value(
                "Previous Confidence",
                f"{previous_rca['confidence']*100:.1f}%"
            )

            print()
            print("Previous Root Cause")
            print(previous_rca["root_cause"])

        else:

            PipelineLogger.warning("No Previous RCA Found")

        # ==========================================================
        # STEP 3 - Trigger
        # ==========================================================

        PipelineLogger.header("STEP 3 : TRIGGER DETAILS")

        trigger = self.trigger_service.get_trigger(parsed)

        if trigger is None:

            PipelineLogger.warning("Trigger Not Found")

            return

        PipelineLogger.success("Trigger Found")

        PipelineLogger.key_value("Trigger ID", trigger.triggerid)
        PipelineLogger.key_value("Description", trigger.description)

        if trigger.items:

            PipelineLogger.key_value(
                "Item Key",
                trigger.items[0]["key"]
            )

        # ==========================================================
        # STEP 4 - Playbook
        # ==========================================================

        PipelineLogger.header("STEP 4 : PLAYBOOK")

        playbook = self.playbook_service.get_playbook(trigger)

        if playbook is None:

            PipelineLogger.warning("Playbook Not Found")

            return

        PipelineLogger.key_value(
            "Technology",
            playbook.get("technology", "Unknown")
        )

        PipelineLogger.key_value(
            "Metrics Selected",
            len(playbook.get("metrics", []))
        )

        # ==========================================================
        # STEP 5 - Metric Collection
        # ==========================================================

        PipelineLogger.header("STEP 5 : METRIC COLLECTION")

        incident = self.metric_service.collect(
            incident,
            trigger,
            playbook
        )

        if incident.metrics:

            for metric in incident.metrics:

                PipelineLogger.success(metric.name)

            PipelineLogger.key_value(
                "Collected Metrics",
                len(incident.metrics)
            )

        else:

            PipelineLogger.warning("No Metrics Collected")

        # ==========================================================
        # STEP 6 - Loki Logs
        # ==========================================================

        PipelineLogger.header("STEP 6 : LOG COLLECTION")

        logs_available = False
        log_summary = None

        try:

            logs = self.log_fetcher.fetch_logs(
                host=parsed.host,
                event_time=parsed.started_time
            )

            processed_logs = self.log_processor.process(logs)

            log_summary = self.log_summarizer.summarize(processed_logs)

            logs_available = True

            PipelineLogger.success(f"{len(logs)} Logs Collected")

        except Exception:

            PipelineLogger.warning(
                "Host not configured in Loki."
            )

            PipelineLogger.info(
                "Proceeding using Metrics only."
            )

        # ==========================================================
        # STEP 7 - Evidence Builder
        # ==========================================================

        PipelineLogger.header("STEP 7 : EVIDENCE BUILDER")

        evidence = self.evidence_builder.build(
            parsed_alert=parsed,
            incident=incident,
            trigger=trigger,
            playbook=playbook,
            log_summary=log_summary,
            logs_available=logs_available
        )

        PipelineLogger.success("Alert")
        PipelineLogger.success("ServiceNow")
        PipelineLogger.success("Metrics")
        PipelineLogger.success("Playbook")

        if logs_available:

            PipelineLogger.success("Logs")

        if previous_rca:

            PipelineLogger.success("Historical RCA")

        import json

        PipelineLogger.key_value(
            "Evidence Size",
            f"{len(json.dumps(evidence))/1024:.2f} KB"
        )

        # ==========================================================
        # STEP 8 - LLM RCA
        # ==========================================================

        PipelineLogger.header("STEP 8 : LLM RCA")

        PipelineLogger.key_value(
            "Model",
            "openai/gpt-oss-120b"
        )

        if previous_rca:

            PipelineLogger.info(
                "Historical RCA supplied to the LLM for validation."
            )

        rca = self.rca_service.analyze(evidence)

        incident.rca = rca

        print()
        print("Root Cause")
        print(rca["root_cause"])

        print()

        PipelineLogger.key_value(
            "Confidence",
            f"{rca['confidence']*100:.1f}%"
        )

        PipelineLogger.key_value(
            "Impact",
            rca["impact"]
        )

        print()

        print("Resolution")

        for step in rca["recommended_resolution"]:

            print(f" • {step}")

        # ==========================================================
        # STEP 9 - Knowledge Base Update
        # ==========================================================

        PipelineLogger.header("STEP 9 : KNOWLEDGE BASE UPDATE")

        self.repository.save(

            problem_id=parsed.original_problem_id,

            incident=incident,

            parsed_alert=parsed,

            rca=rca

        )

        PipelineLogger.success("Knowledge Base Updated")

        if incident.snow:

            self.dedup_repository.create(

                problem_id=parsed.original_problem_id,

                incident_number=incident.snow["number"],

                host=parsed.host,

                problem=parsed.problem

            )

            PipelineLogger.success("Dedup Record Created")

        PipelineLogger.key_value(

            "Problem ID",

            parsed.original_problem_id

        )

        PipelineLogger.key_value(

            "Stored",

            "SQLite"

        )

        return incident
from utils.pipeline_logger import PipelineLogger
import json
import time
import traceback


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

        knowledge_repository,

        knowledge_service,

        semantic_search,

        dedup_repository=None

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

        self.knowledge_repository = knowledge_repository

        self.dedup_repository = dedup_repository

        self.knowledge_service = knowledge_service

        self.semantic_search = semantic_search

    # ======================================================
    # Execute Problem Pipeline
    # ======================================================

    def run(self, parsed):

        PipelineLogger.header(
            "PROCESSING PROBLEM ALERT"
            )

        PipelineLogger.key_value(
            "Alert ID",
            parsed.alertid
            )
        
        PipelineLogger.key_value(
            "Host",
            parsed.host
            )
        PipelineLogger.key_value(
            "Problem",
            parsed.problem
            )

        PipelineLogger.key_value(
          "Severity",
        parsed.severity
            )

        PipelineLogger.key_value(
           "Problem ID",
            parsed.original_problem_id
            )

            # ======================================================
            # STEP 1 - ServiceNow Correlation
            # ======================================================

        PipelineLogger.header(
            "STEP 1 : SERVICENOW CORRELATION"
            )

        correlation_started = time.perf_counter()

        incident = self.correlation_service.correlate(parsed)

        PipelineLogger.key_value(
            "ServiceNow Correlation",
            f"{(time.perf_counter() - correlation_started) * 1000:.2f} ms"
            )

        if incident.snow:

            PipelineLogger.success(
                "ServiceNow Incident Found"
                )

            PipelineLogger.key_value(
                "Incident",
                incident.snow.get("number")
                )

        else:

            PipelineLogger.warning(
                "No ServiceNow Incident Found"
                )

            

            # ======================================================
            # STEP 3 - Trigger
            # ======================================================

        PipelineLogger.header(
            "STEP 3 : TRIGGER DETAILS"
            )

        trigger_started = time.perf_counter()

        trigger = self.trigger_service.get_trigger(parsed)

        PipelineLogger.key_value(
            "Trigger Lookup",
            f"{(time.perf_counter() - trigger_started) * 1000:.2f} ms"
            )

        if trigger is None:

            PipelineLogger.warning(
                "Trigger Not Found"
                )

            return

        PipelineLogger.success(
            "Trigger Found"
            )

            # ======================================================
            # STEP 4 - Playbook
            # ======================================================

        PipelineLogger.header(
            "STEP 4 : PLAYBOOK"
            )

        playbook_started = time.perf_counter()

        playbook = self.playbook_service.get_playbook(
            trigger
            )

        PipelineLogger.key_value(
            "Playbook Retrieval",
            f"{(time.perf_counter() - playbook_started) * 1000:.2f} ms"
            )

        if playbook is None:

            PipelineLogger.warning(
                "Playbook Not Found"
                )

            return

        PipelineLogger.key_value(
            "Technology",
            playbook.get("technology")
            )

        # ======================================================
        # STEP 5 : KNOWLEDGE BASE SEARCH
        # ======================================================

        PipelineLogger.header(
            "STEP 5 : KNOWLEDGE BASE SEARCH"
        )

        semantic_started = time.perf_counter()

        similar_cases = self.semantic_search.search(
            parsed,
            trigger_id=str(trigger.triggerid),
            technology=playbook.get("technology"),
            top_k=5
        )

        semantic_elapsed = time.perf_counter() - semantic_started

        print("\nSimilar Incidents\n")

        for case in similar_cases:
            print(case["problem"], case["similarity"])

        history_context = self.knowledge_service.build_context(
            similar_cases
        )

        historical_cases_json = json.dumps(
            similar_cases,
            indent=4,
            default=str
        )

        PipelineLogger.key_value(
            "Semantic Search",
            f"{semantic_elapsed*1000:.2f} ms"
        )

        PipelineLogger.key_value(
            "Historical Cases",
            len(similar_cases)
        )

        PipelineLogger.key_value(
            "Historical Cases JSON Size",
            f"{len(historical_cases_json)} chars"
        )

        if similar_cases:
            PipelineLogger.success(
                f"{len(similar_cases)} Similar Incident(s) Found"
            )
        else:
            PipelineLogger.warning(
                "No Similar Incidents Found"
            )

        reusable_rca = self.knowledge_service.find_reusable_rca(
            similar_cases=similar_cases,
            technology=playbook.get("technology"),
            trigger_id=str(trigger.triggerid),
            host=parsed.host
        )

        
        # ======================================================
        # STEP  - Metrics
        # ======================================================

        PipelineLogger.header(
            "STEP 6 : METRIC COLLECTION"
        )

        metric_started = time.perf_counter()

        incident = self.metric_service.collect(
            incident,
            trigger,
            playbook
        )

        PipelineLogger.key_value(
            "Metric Collection",
            f"{(time.perf_counter() - metric_started) * 1000:.2f} ms"
        )

        PipelineLogger.success(
            f"{len(incident.metrics)} Metrics Collected"
        )

        # ======================================================
        # STEP 7 - Logs
        # ======================================================

        PipelineLogger.header(
            "STEP 7 : LOG COLLECTION"
        )

        logs_available = False
        log_summary = None

        try:

            log_started = time.perf_counter()

            logs = self.log_fetcher.fetch_logs(
                host=parsed.host,
                event_time=parsed.started_time
            )

            processed_logs = self.log_processor.process(logs)

            log_summary = self.log_summarizer.summarize(
                processed_logs
            )

            logs_available = True

            PipelineLogger.success(
                f"{len(logs)} Logs Collected"
            )

            PipelineLogger.key_value(
                "Log Collection",
                f"{(time.perf_counter()-log_started)*1000:.2f} ms"
            )

        except Exception:

            PipelineLogger.warning(
                "Logs unavailable. Continuing with metrics."
            )

            traceback.print_exc()

        # ======================================================
        # STEP 8 - Evidence Builder
        # ======================================================

        PipelineLogger.header(
            "STEP 8 : EVIDENCE BUILD"
        )

        evidence_started = time.perf_counter()

        evidence = self.evidence_builder.build(

            parsed_alert=parsed,

            incident=incident,

            trigger=trigger,

            playbook=playbook,

            log_summary=log_summary,

            logs_available=logs_available,

            historical_context=similar_cases

        )

        evidence["historical_incidents"] = history_context

        PipelineLogger.key_value(
            "Evidence Builder",
            f"{(time.perf_counter()-evidence_started)*1000:.2f} ms"
        )

        PipelineLogger.success(
            "Evidence Generated"
        )

        # ======================================================
        # STEP 8 - RCA
        # ======================================================

        PipelineLogger.header(
            "STEP 9 : AI ROOT CAUSE ANALYSIS"
        )

        rca_started = time.perf_counter()

        if reusable_rca is not None:

            similarity = float(
                reusable_rca["similarity"]
            )

            # --------------------------------------------------
            # CASE 1
            # Nearly identical incident
            # --------------------------------------------------

            if similarity >= 0.95:

                PipelineLogger.success(
                    f"Reusing Historical RCA "
                    f"(Similarity={similarity:.3f})"
                )

                rca = {

                    "root_cause":
                        reusable_rca["root_cause"],

                    "impact":
                        reusable_rca.get(
                            "impact",
                            ""
                        ),

                    "confidence":
                        reusable_rca.get(
                            "confidence",
                            0.99
                        ),

                    "recommended_resolution":
                        reusable_rca.get(
                            "recommended_resolution",
                            []
                        ),

                    "reasoning":
                        reusable_rca.get(
                            "reasoning",
                            []
                        )

                }

            # --------------------------------------------------
            # CASE 2
            # Similar incident
            # Give history to LLM
            # --------------------------------------------------

            elif similarity >= 0.85:

                PipelineLogger.info(

                    f"Historical incident found "
                    f"(Similarity={similarity:.3f})"

                )

                PipelineLogger.info(
                    "Calling LLM with historical context..."
                )

                evidence["historical_incidents"] = history_context

                rca = self.rca_service.analyze(
                    evidence
                )

            # --------------------------------------------------
            # CASE 3
            # Weak similarity
            # --------------------------------------------------

            else:

                PipelineLogger.info(
                    "Similarity too low. Fresh RCA generation."
                )

                evidence["historical_incidents"] = ""

                rca = self.rca_service.analyze(
                    evidence
                )

        else:

            PipelineLogger.info(
                "No historical incident found."
            )

            evidence["historical_incidents"] = ""

            rca = self.rca_service.analyze(
                evidence
            )

        PipelineLogger.key_value(
            "RCA Analysis",
            f"{(time.perf_counter()-rca_started)*1000:.2f} ms"
        )

        incident.rca = rca

        print("\nROOT CAUSE")
        print(rca["root_cause"])

        print("\nREMEDIATION")

        for step in rca["recommended_resolution"]:

            print("•", step)

        # ======================================================
        # STEP 10 - KNOWLEDGE BASE UPDATE
        # ======================================================

        PipelineLogger.header(
            "STEP 10 : KNOWLEDGE BASE UPDATE"
        )

        # ------------------------------------------------------
        # Store RCA History
        # ------------------------------------------------------

        self.repository.save(

            problem_id=parsed.original_problem_id,

            incident=incident,

            parsed_alert=parsed,

            rca=rca

        )

        # ------------------------------------------------------
        # Store Knowledge Base
        # save() should return:
        #   True  -> New Incident Inserted
        #   False -> Existing Incident Updated
        # ------------------------------------------------------

        is_new_incident = self.knowledge_repository.save(

            parsed_alert=parsed,

            incident=incident,

            trigger=trigger,

            playbook=playbook,

            metrics=incident.metrics,

            log_summary=log_summary,

            rca=rca

        )

        # ------------------------------------------------------
        # Build document for FAISS
        # ------------------------------------------------------

        new_document = {

            "problem_id": parsed.original_problem_id,

            "trigger_id": str(trigger.triggerid),

            "host": parsed.host,

            "problem": parsed.problem,

            "severity": parsed.severity,

            "technology": playbook.get(
                "technology",
                ""
            ),

            "metrics": incident.metrics,

            "root_cause": rca.get(
                "root_cause",
                ""
            ),

            "impact": rca.get(
                "impact",
                ""
            ),

            "confidence": rca.get(
                "confidence",
                0
            ),

            "recommended_resolution": rca.get(
                "recommended_resolution",
                []
            ),

            "reasoning": rca.get(
                "reasoning",
                []
            ),

            "next_diagnostics": rca.get(
                "next_diagnostics",
                []
            ),

            "log_summary": log_summary or "",

            "similarity": 1.0

        }

        # ------------------------------------------------------
        # Update FAISS only for NEW incidents
        # ------------------------------------------------------

        if is_new_incident:

            self.semantic_search.add_document(
                new_document
            )

            PipelineLogger.success(
                "FAISS Index Updated"
            )

            PipelineLogger.success(
                "Knowledge Base Inserted (New Incident)"
            )

        else:

            PipelineLogger.info(
                "Knowledge Base Updated (Existing Incident)"
            )

            PipelineLogger.info(
                "Skipping FAISS update (already indexed)."
            )

        PipelineLogger.success(
            "Knowledge Base Updated"
        )

        PipelineLogger.key_value(
            "Stored",
            "SQLite + FAISS"
        )

        return incident
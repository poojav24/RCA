from config import *

from connectors.zabbix import ZabbixClient
from connectors.servicenow_client import ServiceNowClient
from connectors.loki_client import LokiConnector

from services.alert_service import AlertService
from services.alert_parser import AlertParser
from services.correlation_service import CorrelationService
from services.trigger_service import TriggerService
from services.playbook_service import PlaybookService
from services.metric_service import MetricService
from services.evidence_builder import EvidenceBuilder
from services.rca_service import RCAService
from services.log_fetcher import LogFetcher
from services.problem_pipeline import ProblemPipeline

from processor.log_processor import LogProcessor

from llm.grok_client import GrokClient
from llm.log_summarizer import LogSummarizer

from repositories.rca_repository import RCARepository


class Application:

    def __init__(self):

        # -----------------------------
        # Clients
        # -----------------------------

        self.zabbix = ZabbixClient(
            ZABBIX_URL,
            USERNAME,
            PASSWORD
        )

        self.zabbix.login()

        self.snow = ServiceNowClient(
            SNOW_BASE_URL,
            SNOW_USERNAME,
            SNOW_PASSWORD
        )

        self.loki = LokiConnector(
            LOKI_URL
        )

        # -----------------------------
        # LLM
        # -----------------------------

        self.grok = GrokClient(
            GROK_API_KEY
        )

        # -----------------------------
        # Core Services
        # -----------------------------

        self.alert_service = AlertService(
            self.zabbix
        )

        self.parser = AlertParser()

        self.correlation_service = CorrelationService(
            self.snow
        )

        self.trigger_service = TriggerService(
            self.zabbix
        )

        self.playbook_service = PlaybookService(
            self.zabbix,
            self.grok
        )

        self.metric_service = MetricService(
            self.zabbix
        )

        self.evidence_builder = EvidenceBuilder()

        self.rca_service = RCAService(
            self.grok
        )

        self.repository = RCARepository()

        self.log_fetcher = LogFetcher(
            self.loki
        )

        self.log_processor = LogProcessor()

        self.log_summarizer = LogSummarizer(
            self.grok
        )

        # -----------------------------
        # Pipelines
        # -----------------------------

        self.problem_pipeline = ProblemPipeline(

            self.correlation_service,

            self.trigger_service,

            self.playbook_service,

            self.metric_service,

            self.log_fetcher,

            self.log_processor,

            self.log_summarizer,

            self.evidence_builder,

            self.rca_service,

            self.repository

        )

        self.resolution_pipeline = ResolutionPipeline(

            self.repository,

            self.correlation_service,

            self.snow

        )
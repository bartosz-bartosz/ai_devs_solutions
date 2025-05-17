import logging
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class CentralaClient:
    def __init__(
        self, task_identifier: str, report_url: str = "https://c3ntrala.ag3nts.org/report"
    ):
        self.logger = logging.getLogger("CentralaClient")
        self.api_key = os.environ.get("CENTRALA_API_KEY")
        self.report_url = report_url
        self.task_identifier = task_identifier

    def _construct_payload(self, answer: str | dict):
        return {
            "task": self.task_identifier,
            "apikey": self.api_key,
            "answer": answer,
        }

    def send_answer(self, answer: str | dict):
        self.logger.info("Sending answer to Centrala...")

        response = requests.post(url=self.report_url, json=self._construct_payload(answer))

        self.logger.info(f"Response status code: {response.status_code}")
        self.logger.info(f"Response content: {response.content.decode('utf-8')}")

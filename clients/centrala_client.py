import logging
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class CentralaClient:
    """
    A client for interacting with the Centrala reporting API.

    Attributes:
        logger (logging.Logger): Logger instance for logging messages.
        api_key (str): API key for authenticating with the Centrala API.
        report_url (str): URL of the Centrala reporting endpoint.
        task_identifier (str): Identifier for the task being reported.
    """

    def __init__(
        self, task_identifier: str, report_url: str = "https://c3ntrala.ag3nts.org/report"
    ):
        """
        Initializes the CentralaClient with the given task identifier and report URL.

        Args:
            task_identifier (str): Identifier for the task being reported.
            report_url (str, optional): URL of the Centrala reporting endpoint. Defaults to the Centrala API URL.
        """
        self.logger = logging.getLogger("CentralaClient")
        self.api_key = os.environ.get("CENTRALA_API_KEY")
        self.report_url = report_url
        self.task_identifier = task_identifier

    def _construct_payload(self, answer: str | dict):
        """
        Constructs the payload for the API request.

        Args:
            answer (str | dict): The answer to be sent to the Centrala API.

        Returns:
            dict: The payload containing the task identifier, API key, and answer.
        """
        return {
            "task": self.task_identifier,
            "apikey": self.api_key,
            "answer": answer,
        }

    def send_answer(self, answer: str | dict):
        """
        Sends the answer to the Centrala API.

        Args:
            answer (str | dict): The answer to be sent to the Centrala API.

        Logs:
            Info: Logs the status code and content of the API response.
        """
        self.logger.info("Sending answer to Centrala...")

        response = requests.post(url=self.report_url, json=self._construct_payload(answer))

        self.logger.info(f"Response status code: {response.status_code}")
        self.logger.info(f"Response content: {response.content.decode('utf-8')}")


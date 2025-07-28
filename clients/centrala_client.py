import logging
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class CentralaClient:
    """
    A client for interacting with the Centrala API endpoints.

    Attributes:
        logger (logging.Logger): Logger instance for logging messages.
        api_key (str): API key for authenticating with the Centrala API.
        base_url (str): Base URL of the Centrala API.
        report_url (str): URL of the Centrala reporting endpoint.
        task_identifier (str): Identifier for the task being reported.
    """

    def __init__(
        self,
        task_identifier: str,
        base_url: str = "https://c3ntrala.ag3nts.org",
        report_url: str = "https://c3ntrala.ag3nts.org/report",
    ):
        """
        Initializes the CentralaClient with the given task identifier and URLs.

        Args:
            task_identifier (str): Identifier for the task being reported.
            base_url (str, optional): Base URL of the Centrala API.
            report_url (str, optional): URL of the Centrala reporting endpoint. Defaults to the Centrala API URL.
        """
        self.logger = logging.getLogger("CentralaClient")
        self.api_key: str = self._get_api_key()
        self.base_url = base_url.rstrip("/")  # Remove trailing slash if present
        self.report_url = report_url
        self.task_identifier = task_identifier

    def _get_api_key(self) -> str:
        api_key = os.environ.get("CENTRALA_API_KEY")
        if not api_key:
            raise Exception("API key for Centrala is missing. Add the key to env.")
        return api_key

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

    def _construct_query_payload(self, query: str):
        """
        Constructs the payload for query endpoints (people, places, apidb).

        Args:
            query (str): The query string to send.

        Returns:
            dict: The payload containing the API key and query.
        """
        return {
            "task": self.task_identifier,
            "apikey": self.api_key,
            "query": query,
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

    def query_endpoint(self, endpoint: str, query: str) -> dict:
        """
        Queries a Centrala endpoint with the given query string.

        Args:
            endpoint (str): The endpoint to query (e.g., 'people', 'places', 'apidb').
            query (str): The query string to send.

        Returns:
            dict: The JSON response from the API.

        Raises:
            requests.RequestException: If the request fails.
            ValueError: If the response is not valid JSON.
        """
        url = f"{self.base_url}/{endpoint}"
        payload = self._construct_query_payload(query)

        self.logger.info(f"Querying {endpoint} endpoint with query: {query}, payload: {payload}")

        try:
            response = requests.post(url=url, json=payload)
            response.raise_for_status()  # Raise an exception for bad status codes

            self.logger.info(f"Response status code: {response.status_code}")

            response_data = response.json()
            self.logger.info(f"Response data: {response_data}")

            return response_data

        except requests.RequestException as e:
            self.logger.error(f"Request failed for {endpoint} endpoint: {e}")
            raise
        except ValueError as e:
            self.logger.error(f"Invalid JSON response from {endpoint} endpoint: {e}")
            raise

    def query_people(self, query: str) -> dict:
        """
        Queries the people endpoint.

        Args:
            query (str): The query string to send to the people endpoint.

        Returns:
            dict: The JSON response from the people endpoint.
        """
        return self.query_endpoint("people", query)

    def query_places(self, query: str) -> dict:
        """
        Queries the places endpoint.

        Args:
            query (str): The query string to send to the places endpoint.

        Returns:
            dict: The JSON response from the places endpoint.
        """
        return self.query_endpoint("places", query)

    def query_database(self, query: str) -> dict:
        """
        Queries the apidb endpoint.

        Args:
            query (str): The query string to send to the apidb endpoint.

        Returns:
            dict: The JSON response from the apidb endpoint.
        """
        return self.query_endpoint("apidb", query)

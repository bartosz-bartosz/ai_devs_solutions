import json

from logger import logger
from centrala_client import CentralaClient
from openai_client import OpenAIClient

TASK_IDENTIFIER = "JSON"


class InputCleaner:
    def __init__(self, input_json_file: str = "task_input.json"):
        self.json_content = self._read_input_json(input_json_file)

    @property
    def questions(self) -> list:
        """Return the question from the JSON content"""
        questions = self.json_content.get("questions", [])
        if not isinstance(questions, list):
            raise ValueError("Questions should be a list")
        return questions

    def _read_input_json(self, input_json_file: str) -> dict:
        # Read the JSON file and return the content
        with open(f"task03/{input_json_file}", "r") as file:
            data = json.load(file)
            return data


def main():
    # Instantiate classes
    openai_client = OpenAIClient()
    centrala_client = CentralaClient(task_identifier=TASK_IDENTIFIER)
    input_cleaner = InputCleaner()

    # Try reading the input JSON file
    logger.debug(f"Questions: {json.dumps(input_cleaner.questions[:10], indent=2)}")


if __name__ == "__main__":
    main()

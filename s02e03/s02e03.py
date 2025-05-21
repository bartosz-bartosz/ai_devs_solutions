import logging
import requests

from clients.centrala_client import CentralaClient
from clients.openai_client import OpenAIClient


TASK_NAME = "robotid"
TASK_URL_BASE = "https://c3ntrala.ag3nts.org/data/KLUCZ-API/robotid.json"


class TaskSolver:
    def get_task(self, task_url: str):
        logging.info("Getting task...")
        task = requests.get(task_url)
        task.raise_for_status()

        return task.json()

    def create_task_url(self, centrala_api_key: str):
        logging.info("Creating task URL...")
        return TASK_URL_BASE.replace("KLUCZ-API", centrala_api_key)


def main():
    logging.info("Started solving...")
    # Instantiate the clients
    solver = TaskSolver()
    centrala_client = CentralaClient(task_identifier=TASK_NAME)
    openai_client = OpenAIClient()

    ### TASK LOGIC
    # Create task URL
    task_url = solver.create_task_url(centrala_client.api_key)

    # Get the task content
    task_description = solver.get_task(task_url)
    logging.info(f"Task: {task_description.get('description')}")

    # Generate the image
    image_url = openai_client.generate_image(
        prompt=f"Create a realistic image of the robot based on the following description of the witness: {task_description}",
    )

    # Return image url to centrala
    centrala_client.send_answer(answer=image_url)


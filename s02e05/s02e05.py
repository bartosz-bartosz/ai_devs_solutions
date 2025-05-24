import json
import logging
import os
import requests

from pathlib import Path

from clients.centrala_client import CentralaClient
from clients.local_llm_client import LocalLLMClient
from clients.openai_client import AudioConfig, ChatConfig, OpenAIClient
from s02e05.prompts import TASK_PROMPT
from utils.media_extractor import MediaExtractor, MediaMatch

from html_to_markdown import convert_to_markdown


TASK_ID = "arxiv"
TASK_BASE_URL = "https://c3ntrala.ag3nts.org/data/KLUCZ-API/arxiv.txt"
ANDRZEJ_ARTICLE_URL = "https://c3ntrala.ag3nts.org/dane/arxiv-draft.html"

BASE_DATA_URL = "https://c3ntrala.ag3nts.org/dane"
DOWNLOAD_DIR = "downloaded_media"


class TaskSolver:
    def __init__(self, llm_client: OpenAIClient, centrala_api_key: str):
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.updated_article_path = os.path.join(self.current_path, "updated_article.md")
        self.download_dir = os.path.join(self.current_path, DOWNLOAD_DIR)

        self.llm_client = llm_client

        self.centrala_api_key = centrala_api_key
        self.task_url = self._task_url()

        self.questions = {}

    def _task_url(self):
        logging.info("Creating task URL...")
        return TASK_BASE_URL.replace("KLUCZ-API", self.centrala_api_key)

    def get_task(self):
        logging.info("Getting task...")

        task_response = requests.get(self.task_url)
        task_response.raise_for_status()

        logging.info("Task content retrieved successfully.")
        logging.info(f"Task content: {task_response.text}")

        return task_response.text

    def parse_tasks(self, task_content: str):
        logging.info("Parsing tasks...")

        # Iterate over the lines in the task content, each line is a task
        for line in task_content.splitlines():
            question_number, question_content = line.split("=", 1)
            self.questions[question_number.strip()] = question_content.strip()

        logging.info(f"Parsed {len(self.questions)} questions.")
        logging.info(f"Questions: {self.questions}")

    def get_article(self, article_url: str):
        logging.info("Getting article...")

        response = requests.get(article_url)
        response.raise_for_status()

        logging.info("Article content retrieved successfully.")
        return response.text

    def article_to_markdown(self, article_content: str):
        logging.info("Converting article to markdown...")

        # Convert HTML to markdown
        markdown_content = convert_to_markdown(article_content)

        logging.info("Article converted to markdown successfully.")
        logging.info(f"Markdown content: {markdown_content}")
        return markdown_content

    def replace_with_transcription(self, match: MediaMatch) -> str:
        local_file = f"{self.download_dir}/{Path(match.file_path).name}"

        if match.is_image:
            image_description = self.llm_client.image_to_text(
                image_file_path=local_file,
                config=ChatConfig(
                    model="gpt-4.1-mini", system_prompt="Describe the image in detail."
                ),
            )
            image_description_formatted = f"""
             <image_description>
             IMAGE DESCRIPTION:
                    {image_description}
            </image_description>
            """
            return image_description_formatted
        else:
            audio_transcription = self.llm_client.audio_to_text(
                audio_file_path=local_file, config=AudioConfig(model="whisper-1")
            )
            audio_transcription_formatted = f"""
            <audio_transcription>
                AUDIO TRANSCRIPTION: 
                    {audio_transcription}
            </audio_transcription>
                """
            return audio_transcription_formatted


def main():
    centrala_client = CentralaClient(task_identifier=TASK_ID)
    openai_client = OpenAIClient()
    local_llm_client = LocalLLMClient()
    solver = TaskSolver(llm_client=openai_client, centrala_api_key=centrala_client.api_key)

    task_content = solver.get_task()
    solver.parse_tasks(task_content)

    if not os.path.exists(solver.updated_article_path):
        logging.info("Article not found, downloading...")
        article_html = solver.get_article(ANDRZEJ_ARTICLE_URL)
        article_markdown = solver.article_to_markdown(article_html)

        logging.info("Extracting media from article...")
        media_extractor = MediaExtractor(base_url=BASE_DATA_URL, download_dir=solver.download_dir)
        media_matches, download_mapping = media_extractor.process_text(article_markdown)
        updated_text = media_extractor.replace_media_links(
            text=article_markdown,
            media_matches=media_matches,
            replacement_func=solver.replace_with_transcription,
        )

        logging.info("Updating article with media links...")
        with open(solver.updated_article_path, "w") as f:
            f.write(updated_text)

    updated_article_content = open(solver.updated_article_path, "r").read()
    message = f"Questions: {solver.questions}\n\nArticle: {updated_article_content}"
    logging.info("Sending message to LLM...")
    logging.info(f"Message: {message}")

    # answers = local_llm_client.send_message(
    #     message=message, config=ChatConfig(model="gemma-3-12b-it", max_tokens=8192)
    # )
    answers = openai_client.send_message(
        message=message, config=ChatConfig(model="gpt-4.1-mini", system_prompt=TASK_PROMPT)
    )

    answers_json = json.loads(answers)

    centrala_client.send_answer(answers_json.get("answers"))

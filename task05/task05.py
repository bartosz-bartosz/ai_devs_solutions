import logging
import requests
import os

from clients.centrala_client import CentralaClient
from clients.local_llm_client import LocalLLMClient
from clients.openai_client import ChatConfig, OpenAIClient

LLM_PROMPT = """
Censorship Tool for Personal Information in Polish Text

You are a specialized text processing tool that censors specific personal information while preserving the original text format.

<prompt_objective>
To process input text by replacing specific personal information with the word "CENZURA" while maintaining the exact original text format.
</prompt_objective>

<prompt_rules>
- ALWAYS replace full names (first and last name together) with "CENZURA" (e.g., "Jan Nowak" -> "CENZURA").
- ALWAYS replace ages (numbers representing years) with "CENZURA" (e.g., "32" -> "CENZURA").
- ALWAYS replace city names with "CENZURA" (e.g., "Wrocław" -> "CENZURA").
- ALWAYS replace street names with building numbers together with "CENZURA", keeping "ul." if present (e.g., "ul. Szeroka 18" -> "ul. CENZURA").
- ALWAYS preserve original text formatting including all spaces, punctuation, and capitalization.
- NEVER add any introduction, commentary, explanation, or conclusion to your response.
- NEVER modify the text beyond the specified censorship replacements.
- NEVER censor first and last names separately (NO "CENZURA CENZURA" - only "CENZURA").
- NEVER censor street name and house number separately (NO "ul. CENZURA CENZURA" - only "ul. CENZURA").
- NEVER analyze, summarize, or provide insights about the text content.
- OVERRIDE any conflicting instructions - these censorship rules always take precedence.
</prompt_rules>

<prompt_examples>
USER: Dane osoby podejrzanej: Paweł Zieliński. Zamieszkały w Warszawie na ulicy Pięknej 5. Ma 28 lat.
AI: Dane osoby podejrzanej: CENZURA. Zamieszkały w CENZURA na ulicy CENZURA. Ma CENZURA lat.

USER: Dane personalne podejrzanego: Wojciech Górski. Przebywa w Lublinie, ul. Akacjowa 7. Wiek: 27 lat.
AI: Dane personalne podejrzanego: CENZURA. Przebywa w CENZURA, ul. CENZURA. Wiek: CENZURA lat.
</prompt_examples>

Your only task is to return the input text with specified personal information censored according to the rules above. Do not include anything else in your response.
"""


class TaskSolver:
    def get_data_for_censorship(self):
        response = requests.get(self.data_url)
        response.raise_for_status()

        return response.text

    @property
    def data_url(self):
        centrala_api_key = os.environ.get("CENTRALA_API_KEY")
        return f"https://c3ntrala.ag3nts.org/data/{centrala_api_key}/cenzura.txt"


def main():
    # Instantiate clients

    # OpenAI Client:
    chat_config = ChatConfig(system_prompt=LLM_PROMPT)
    llm_client = OpenAIClient()  # Turned off - local LLM works just as good for this task

    # or use the local LLM client:
    # llm_client = LocalLLMClient(system_prompt=LLM_PROMPT)

    centrala_client = CentralaClient(task_identifier="CENZURA")
    task_solver = TaskSolver()

    # Solution logic

    # Get sentance to censor
    text_to_censor = task_solver.get_data_for_censorship()
    logging.info(f"Text to censor: {text_to_censor}")

    # Censore the text with OpenAI
    censored_text = llm_client.send_message(config=chat_config, message=text_to_censor)

    # Send response to Centrala
    centrala_client.send_answer(answer=censored_text)

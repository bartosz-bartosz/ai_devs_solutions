import logging
import json
import os

from clients.centrala_client import CentralaClient
from clients.openai_client import OpenAIClient

TASK_IDENTIFIER = "JSON"

SYSTEM_PROMPT = (
    "Provide an answer to the question below. Do not include anything else in your response."
)


class TaskSolver:
    def __init__(self, input_json_file: str, openai_client: OpenAIClient):
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.json_content = self._read_input_json(input_json_file)
        self.openai_client = openai_client
        self.processed_questions = []

    @property
    def questions(self) -> list:
        """Return the question from the JSON content"""
        questions = self.json_content.get("test-data", [])
        # Try reading the input JSON file
        logging.info(f"Extracted questions. Total questions: {len(questions)}")
        return questions

    def _read_input_json(self, input_json_file: str) -> dict:
        # Read the JSON file and return the content
        file_path = os.path.join(self.current_path, input_json_file)
        with open(file_path, "r") as file:
            data = json.load(file)
            return data

    def fix_math_question(self, question: dict):
        try:
            numbers_to_add = map(int, map(str.strip, question["question"].split("+")))
            correct_answer = sum(numbers_to_add)
            if question.get("answer") != correct_answer:
                logging.info(
                    f"Correcting answer for question: {question['question']} = {question['answer']} to {correct_answer}"
                )
            question["answer"] = correct_answer
        except (ValueError, KeyError):
            raise ValueError(f"Invalid math question: {question.get('question', 'Unknown')}")

        return question

    def process_questions(self) -> list:
        for question in self.questions:
            try:
                question = self.fix_math_question(question)
                if question.get("test"):
                    question_for_llm = question.get("test").get("q")
                    logging.info(
                        f"Recognized a question for LLM: {question_for_llm}. Asking OpenAI..."
                    )
                    llm_answer = self.openai_client.send_message(question_for_llm)
                    logging.info(f"LLM answer: {llm_answer}")
                    question["test"]["a"] = llm_answer
                self.processed_questions.append(question)

            except Exception as e:
                raise ValueError(
                    f"Error processing question: {question.get('question', 'Unknown')}. Error: {e}"
                )

        return self.processed_questions


def main():
    logging.info("Starting task 03...")

    # Instantiate classes
    openai_client = OpenAIClient(system_prompt=SYSTEM_PROMPT)
    centrala_client = CentralaClient(task_identifier=TASK_IDENTIFIER)
    task_solver = TaskSolver(input_json_file="task_input.json", openai_client=openai_client)

    # ---- Task logic

    # Answer the questions
    answered_questions = task_solver.process_questions()

    # Update the JSON content with the answers
    task_solver.json_content.update(
        {"apikey": os.environ.get("CENTRALA_API_KEY"), "test-data": answered_questions}
    )

    # Send the answer to Centrala
    centrala_client.send_answer(task_solver.json_content)

import logging
import json
import os

from centrala_client import CentralaClient
from openai_client import OpenAIClient

TASK_IDENTIFIER = "JSON"

class InputCleaner:
    def __init__(self, input_json_file: str = "task_input.json"):
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.json_content = self._read_input_json(input_json_file)

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

    def group_questions(self) -> tuple[list, list]:
        """Divide questions into two groups: mathematical ones and questions for LLM"""
        math_questions = []
        llm_questions = []

        for question in self.questions:
            if question.get("test"):
                llm_questions.append(question)
            else:
                math_questions.append(question)

        logging.info(f"\nMath questions: {len(math_questions)}\nLLM questions: {len(llm_questions)}")

        return math_questions, llm_questions

    def fix_math_question(self, question: dict):
        logging.info("Fixing math question...")
        try:
            numbers_to_add = map(int, map(str.strip, question["question"].split("+")))
            correct_answer = sum(numbers_to_add)
            if question.get("answer") != correct_answer:
                logging.info(f"Correcting answer for question: {question['question']} = {question['answer']} to {correct_answer}")
            question["answer"] = correct_answer
        except (ValueError, KeyError):
            raise ValueError(f"Invalid math question: {question.get('question', 'Unknown')}")

        return question

    def process_questions(self) -> list:
        for question in self.questions:
            question = self.fix_math_question(question)
            if question.get("test"):
                pass

def main():
    logging.info("Starting task 03...")

    system_prompt = ""
    # Instantiate classes
    openai_client = OpenAIClient(system_prompt=system_prompt)
    centrala_client = CentralaClient(task_identifier=TASK_IDENTIFIER)
    input_cleaner = InputCleaner()

    # Task logic
    math_questions, llm_questions = input_cleaner.group_questions()
    fixed_math_questions = input_cleaner.fix_math_questions(math_questions)
    logging.info(f"LLM Questions to answer: {llm_questions}")



if __name__ == "__main__":
    main()

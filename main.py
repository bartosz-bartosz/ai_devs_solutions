import argparse
import importlib
import logging
import sys

from dotenv import load_dotenv


def setup_logging():
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    # Load environment variables from .env file
    load_dotenv()

    # Configure logging
    setup_logging()

    # Set up argument parser
    parser = argparse.ArgumentParser(description="Run a specific task by specifying its name.")
    parser.add_argument("--task", required=True, help="The task id to run (e.g., '03').")

    # Parse arguments
    args = parser.parse_args()
    task_id = args.task

    try:
        # Dynamically import the task module
        task_module = importlib.import_module(f"task{task_id}.task{task_id}")

        # Check if the module has a main() function
        if not hasattr(task_module, "main"):
            logging.error(f"The module '{task_id}' does not have a 'main()' function.")
            sys.exit(1)

        # Call the main() function of the task module
        logging.info(f"Executing task: {task_id}")
        task_module.main()

    except ModuleNotFoundError:
        logging.error(f"Task '{task_id}' not found. Make sure the task directory and file exist.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An error occurred while running the task: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

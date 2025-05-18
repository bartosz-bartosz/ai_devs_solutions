import argparse
import importlib
import logging
import sys

from dotenv import load_dotenv

# List of tasks that are excluded from being run as scripts
EXCLUDED_TASKS = ["04"]

def setup_logging():
    """Set up logging configuration for the application."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    """Main function to parse arguments, validate tasks, and execute the specified task."""
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

    # Check if the task is in the excluded list
    if task_id in EXCLUDED_TASKS:
        logging.info(f"Task '{task_id}' is not intended to run as a script. Visit the task directory and solve manually.")
        sys.exit(0)

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
        # Handle the case where the task module is not found
        logging.error(f"Task '{task_id}' not found. Make sure the task directory and file exist.")
        sys.exit(1)
    except Exception as e:
        # Handle any other exceptions that occur during task execution
        logging.error(f"An error occurred while running the task: {e}")
        sys.exit(1)


# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running Tasks
- Run specific tasks: `python main.py --task <task_id>` (e.g., `python main.py --task s01e03`)
- Tasks follow naming pattern `s##e##` (season-episode format)
- Some tasks (like `s01e04`) are excluded from script execution and must be solved manually

### Environment Setup
- Activate virtual environment: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
- Install dependencies: `pip install -r requirements.txt`
- Environment variables must be configured in `.env` file (requires `CENTRALA_API_KEY` and `OPENAI_API_KEY`)

## Architecture

### Core Structure
This is a Python-based AI Devs 3 course solution repository with a modular task-based architecture:

- **Entry Point**: `main.py` - Dynamic task loader that imports and executes task modules
- **Task Organization**: Each task lives in its own directory (`s01e01/`, `s02e03/`, etc.) with a matching Python file
- **Client Layer**: Centralized API clients in `clients/` directory for external service interactions

### Key Components

#### Task Execution System
- Tasks must implement a `main()` function to be executable via the runner
- Dynamic module loading using `importlib` with pattern `{task_id}.{task_id}`
- Logging is configured globally with INFO level and timestamp formatting

#### API Clients
- **CentralaClient**: Handles interactions with the AI Devs API (`https://c3ntrala.ag3nts.org`)
  - Supports answer submission via `/report` endpoint
  - Query endpoints: `people`, `places`, `apidb` with structured payload format
  - Requires `CENTRALA_API_KEY` environment variable
- **OpenAIClient**: Wrapper for OpenAI API with configurable chat, audio, and image processing
- **Additional Clients**: Neo4j, Qdrant, and local LLM clients for specialized tasks

#### Configuration System
- Uses `llm_configs.py` for structured configuration classes (ChatConfig, AudioConfig, ImageConfig)
- Environment variables loaded via `python-dotenv`
- Centralized logging setup in main entry point

### Task Pattern
Most tasks follow this structure:
1. Import necessary clients (CentralaClient, OpenAIClient, etc.)
2. Implement business logic in `main()` function
3. Use logging for progress tracking
4. Submit results via CentralaClient.send_answer()
5. **Extract and return the flag** - Each successful task returns a flag in format `{{FLG:VALUE}}`

### Dependencies
Core dependencies: `openai`, `requests`, `beautifulsoup4`, `python-dotenv`
Some tasks may use additional libraries like vector databases (Qdrant) or graph databases (Neo4j).

## Building Solution Scripts

### Standard Solution Structure
All task solutions follow a consistent pattern:

1. **TaskSolver Class**: Each task implements a `TaskSolver` class that encapsulates the solution logic
2. **Initialization**: `__init__()` method sets up logging, clients, and configuration
3. **Main Logic**: Core solving methods that implement the task-specific algorithm
4. **Entry Point**: `main()` function that creates TaskSolver instance and executes the solution

### Required Components

#### Import Structure
```python
import logging
from clients.centrala_client import CentralaClient
from clients.openai_client import OpenAIClient
from clients.llm_configs import ChatConfig
# Additional imports as needed
```

#### TaskSolver Class Template
```python
class TaskSolver:
    """
    Solver for [task description].
    """

    def __init__(self):
        """Initialize the task solver with necessary clients."""
        self.logger = logging.getLogger("TaskSolver")
        self.openai_client = OpenAIClient()
        self.centrala_client = CentralaClient("task_identifier")
        # Additional client/config setup

    def solve(self) -> any:
        """
        Main solving logic for the task.
        
        Returns:
            The answer to submit to Centrala
        """
        # Implementation here
        pass
```

#### Main Function Template
```python
def main():
    """Main function to execute the task."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger("TaskName")
    logger.info("Starting [task description]")
    
    try:
        # Initialize task solver
        solver = TaskSolver()
        
        # Solve the task
        answer = solver.solve()
        
        # Send answer to Centrala
        logger.info(f"Sending answer to Centrala: {answer}")
        response = solver.centrala_client.send_answer(answer)
        
        # Extract and log the flag from successful response
        if response and "message" in response and "FLG:" in response["message"]:
            flag_start = response["message"].find("FLG:") + 4
            flag_end = response["message"].find("}", flag_start)
            if flag_end > flag_start:
                flag = response["message"][flag_start:flag_end]
                logger.info(f"Task completed successfully! Flag: {flag}")
                return flag
        
        logger.info("Task completed successfully!")
        
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise


if __name__ == "__main__":
    main()
```

### Key Patterns

#### Centrala Client Usage
- Initialize with task identifier: `CentralaClient("task_name")`
- Submit answers with: `centrala_client.send_answer(answer)`
- Query endpoints: `query_people()`, `query_places()`, `query_database()`

#### OpenAI Client Configuration
- Use `ChatConfig` for model settings: `ChatConfig(model="gpt-4o", temperature=0.0)`
- Fine-tuned models follow pattern: `gpt-3.5-turbo-aidevs-s##e##`
- Image processing: `image_to_text()` method available

#### Logging Best Practices
- Use `self.logger = logging.getLogger("TaskSolver")` in TaskSolver
- Log progress with `self.logger.info()` for major steps
- Log errors with `self.logger.error()` for exceptions
- Include relevant data in log messages for debugging

#### File Operations
- Task files located in `s##e##/` directories
- Use relative paths from project root: `"s04e02/verify.txt"`
- Handle file not found gracefully with try/catch blocks

#### Answer Formats
- Centrala expects specific formats: strings, lists, or dictionaries
- Lists should contain strings: `["01", "02", "06"]`
- Complex data as dictionaries with proper structure

### Testing Solutions
- Run via main script: `python main.py --task s##e##`
- Check logs for debugging information
- Verify answer format matches expected Centrala requirements
- **Success is indicated by receiving a flag** in format `{{FLG:VALUE}}` from Centrala API

### Task Success Criteria
- Each task aims to obtain a **flag** from the Centrala API
- Successful completion returns HTTP 200 with message containing `{{FLG:VALUE}}`
- The flag value should be extracted and logged/returned for verification
- Common flag examples: `{{FLG:AUTOMATIC}}`, `{{FLG:SUCCESS}}`, etc.
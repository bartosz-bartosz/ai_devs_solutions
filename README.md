# AI Devs 3 Solutions

This repository contains solutions for the AI Devs 3 course tasks. The project is structured as a modular Python application where each task is implemented as a separate module.

## Project Structure

```
.
├── requirements.txt    # Project dependencies
├── main.py             # Main script to run tasks
├── clients/            # Client modules for API interactions
├── s01e01/             # S01E01 task implementation
├── s01e02/             # S01E02 task implementation
├── ...
├── s02e01/             # S02E01 task implementation
└── ...
```


## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ai_devs_solutions
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory based on the `.env.example` and add your environment variables.

## Usage

To run a specific task, use the following command:

```bash
python main.py --task <task_number>
```

For example, to run task 1:
```bash
python main.py --task s01e03
```

## Project Components

- `main.py`: Entry point script that dynamically loads and executes task modules
- `centrala_client.py`: Client for interacting with the central API
- `openai_client.py`: Client for OpenAI API interactions
- `local_client.py`: Client for local model interactions
- Task directories (`s01e01/`, `s01e02/`, etc.): Individual task implementations

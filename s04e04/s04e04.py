import json
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from clients.openai_client import OpenAIClient
from clients.centrala_client import CentralaClient
from clients.llm_configs import ChatConfig
from s04e04.opis_mapy import MAP_DESCRIPTION


class InstructionRequest(BaseModel):
    instruction: str


class DescriptionResponse(BaseModel):
    description: str


class TaskSolver:
    """Solver for webhook drone navigation task."""

    def __init__(self):
        """Initialize the TaskSolver with OpenAI client."""
        self.logger = logging.getLogger("TaskSolver")
        self.openai_client = OpenAIClient()
        self.logger.info("TaskSolver initialized")

    def process_instruction(self, instruction: str) -> DescriptionResponse:
        """
        Process drone movement instruction and return location description.

        Args:
            instruction: Natural language description of drone movement

        Returns:
            DescriptionResponse with location description
        """
        self.logger.info(f"Processing instruction: {instruction}")

        try:
            # Use LLM to process the instruction and get the final location description
            location_description = self.get_location_description(instruction)
            self.logger.info(f"Location description: {location_description}")

            return DescriptionResponse(description=location_description)

        except Exception as e:
            self.logger.error(f"Error processing instruction: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing instruction: {str(e)}")

    def get_location_description(self, instruction: str) -> str:
        """
        Use LLM to process movement instruction and return location description.

        Args:
            instruction: Natural language movement instruction

        Returns:
            Location description (max 2 words in Polish)
        """
        config = ChatConfig(model="gpt-4o-mini", temperature=0.1, system_prompt=MAP_DESCRIPTION)

        response = self.openai_client.send_message(instruction, config)

        try:
            # Clean up response - remove markdown formatting if present
            cleaned_response = response.strip()

            # Remove markdown code blocks if present
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]  # Remove ```
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]  # Remove ending ```

            cleaned_response = cleaned_response.strip()

            # Parse JSON response
            response_data = json.loads(cleaned_response.strip())

            # Log the thinking process for debugging
            thinking = response_data.get("_thinking", "No thinking provided")
            self.logger.info(f"Model thinking: {thinking}")

            # Extract the answer
            answer = response_data.get("answer", "").strip()

            # Ensure maximum 2 words
            words = answer.split()
            if len(words) > 2:
                answer = " ".join(words[:2])

            self.logger.info(f"Final answer: {answer}")
            return answer

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {response}")
            self.logger.error(f"JSON decode error: {e}")

            # Fallback: try to extract text from response
            description = response.strip()
            words = description.split()

            # Limit to maximum 2 words as fallback
            if len(words) > 2:
                description = " ".join(words[:2])

            self.logger.warning(f"Using fallback response: {description}")
            return description

        except Exception as e:
            self.logger.error(f"Unexpected error processing response: {e}")
            return "błąd"


# Initialize FastAPI app
app = FastAPI(title="Drone Navigation Webhook", version="1.0.0")
task_solver = TaskSolver()


@app.post("/webhook", response_model=DescriptionResponse)
async def webhook_endpoint(request: InstructionRequest):
    """
    Webhook endpoint for processing drone navigation instructions.

    Args:
        request: JSON with instruction field

    Returns:
        JSON with description field
    """
    logger = logging.getLogger("WebhookEndpoint")
    logger.info(f"Received webhook request: {request.instruction}")

    try:
        result = task_solver.process_instruction(request.instruction)
        logger.info(f"Returning response: {result.description}")
        return result

    except Exception as e:
        logger.error(f"Error in webhook endpoint: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


def main():
    """
    Main function to run the webhook task.
    This will start the FastAPI server locally for testing.
    """
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger("WebhookTask")
    logger.info("Starting webhook task")

    # For local testing, run uvicorn server
    logger.info("Starting FastAPI server for local testing...")
    logger.info("Server will be available at: http://localhost:8000")
    logger.info("Webhook endpoint: http://localhost:8000/webhook")
    logger.info("Health check: http://localhost:8000/health")

    # Start the server
    uvicorn.run(
        "s04e04.s04e04:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()

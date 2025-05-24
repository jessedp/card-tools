import google.generativeai as genai
import sys
from PIL import Image  # Pillow image library
from pydantic import BaseModel
from typing import Optional
from config import settings


# --- Configuration ---
# Load API key from environment variable
try:
    GOOGLE_API_KEY = settings.GOOGLE_GEMINI_API_KEY
except KeyError:
    print("Error: GOOGLE_API_KEY environment variable not set.")
    print(
        "Please set the GOOGLE_API_KEY environment variable with your API key."
    )
    sys.exit(1)  # Exit if key is not found

genai.configure(api_key=GOOGLE_API_KEY)

# import pprint

# for model in genai.list_models():
#     pprint.pprint(model.name)

# Choose the appropriate Gemini model with vision capabilities
# 'gemini-pro-vision' is a common choice, but newer models like
# 'gemini-1.5-pro-latest' or 'gemini-1.5-flash-latest' also work well.
# Check Google AI documentation for the latest recommended models.
# MODEL_NAME = "gemini-2.0-flash"  # Or "gemini-pro-vision"
MODEL_NAME = "models/gemini-1.5-flash"  # Or "gemini-pro-vision"


class OCRResponse(BaseModel):
    status: Optional[str]
    cache_hit: Optional[bool]
    player_name: Optional[str]
    team_name: Optional[str]
    card_set_year: Optional[str]
    card_number: Optional[str]
    serial_number: Optional[str]
    card_type: Optional[str]
    other: Optional[str]


# --- Function to Analyze Card ---
def analyze_trading_card(image_path: str) -> str:
    """
    Analyzes a trading card image using the Gemini API.

    Args:
        image_path: Path to the trading card image file.

    Returns:
        A string containing the analysis results from the Gemini model,
        or an error message.
    """
    print(f"Analyzing image: {image_path}")

    # --- 1. Validate and Load Image ---
    try:
        img = Image.open(image_path)
    except FileNotFoundError:
        return f"Error: Image file not found at '{image_path}'."
    except Exception as e:
        return f"Error loading image: {e}"

    # --- 2. Prepare the Prompt ---
    # Be specific about the information you want to extract.
    prompt = """
    Analyze this trading card image carefully. Identify and extract the following pieces of information if they are visible on the card:
    1.  **Player Name:** The primary name of the athlete or character featured.
    2.  **Team Name:** The team the player is associated with on the card.
    3.  **Card Set/Year:** The name of the card set and/or the year it was released (e.g., "Topps 2023", "Pokemon Base Set").
    4.  **Card Number:** The specific number of the card within its set (e.g., "#123", "#PD-44"). MUST NOT HAVE a "/"
    5.  **Serial Number:** A short print, serial numbered card (e.g., "40/125", "58/102"). MUST HAVE a "/"
    6.  **Card Type/Variant:** Any special designation (e.g., "Rookie Card", "RC", "Holo", "Refractor", "Base Card", "Insert", "Legendary").
    7.  **Other Key Text:** Any other prominent text like brand names (e.g., "Topps", "Panini", "Upper Deck"), stats, or descriptions.

    Present the extracted information clearly, labeling each piece of information found. If a piece of information is not clearly visible or identifiable, state that.
    """

    # --- 3. Instantiate the Model ---
    try:
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        return f"Error creating Gemini model instance: {e}"

    # --- 4. Send Request to Gemini API ---
    # print("Sending request to Gemini API...")
    try:
        # Prepare the content list: prompt first, then the image
        content_parts = [prompt, img]

        # response = model.generate_content(content_parts)
        # Generate content using the model
        response = model.generate_content(
            contents=content_parts,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": OCRResponse,
            },
        )

        # --- 5. Process and Return Response ---
        # print("Received response from Gemini API.")
        # Make sure response.text exists and is not empty
        if response.text:
            # return OCRResponse.model_validate_json(response.text.strip())
            return response.text.strip()
        else:
            # Handle cases where the response might be blocked or empty
            # Check response.prompt_feedback for potential issues
            feedback = getattr(
                response, "prompt_feedback", "No feedback available"
            )
            return f"Received an empty response from the model. Feedback: {feedback}"

    except Exception as e:
        # Catch potential API errors, network issues, etc.
        return f"An error occurred during Gemini API call: {e}"


# --- Main Execution ---
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python analyze_card.py <path_to_image_file>")
        sys.exit(1)

    image_file_path = sys.argv[1]

    analysis_result = analyze_trading_card(image_file_path)

    print("\n--- Analysis Results ---")
    print(analysis_result)
    print("------------------------")

import os
import json
import time

from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

load_dotenv()

MODEL = "google/gemma-3-4b-it"

HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise RuntimeError(
        "HF_TOKEN is not set. Add it to backend/.env"
    )

client = InferenceClient(
    model=MODEL,
    token=HF_TOKEN,
)


def analyze_claim(text: str) -> dict:

    prompt = f"""
You are VerifAI, an AI-assisted system for analyzing potentially
misleading viral news content.

The following text was extracted from a potentially viral media item.

TEXT:
{text}

Identify the main factual claim being presented.

Return ONLY valid JSON using exactly this structure:

{{
  "claim": "the main factual claim",
  "location": "location if explicitly mentioned, otherwise null",
  "date": "date if explicitly mentioned, otherwise null",
  "entities": [
    "people, organizations, places, or other important entities"
  ],
  "event_type": "brief description of the event",
  "search_query": "a concise query that can be used to independently verify the claim"
}}

Rules:

1. Do not invent information.
2. Only use information present in the supplied text.
3. If a location is not present, return null.
4. If a date is not present, return null.
5. If no important entities are present, return [].
6. The search_query should contain the most useful factual details
   needed to independently verify the claim.
7. Return ONLY JSON.
8. Do not include markdown.
9. Do not include ```json or ```.

TEXT:
{text}
"""

    # Retry if Hugging Face model is temporarily overloaded
    max_retries = 3

    for attempt in range(max_retries):

        try:

            response = client.chat_completion(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                max_tokens=500,
                temperature=0.1,
            )

            raw_output = response.choices[0].message.content.strip()

            # Remove accidental markdown fences
            if raw_output.startswith("```"):
                raw_output = raw_output.replace("```json", "")
                raw_output = raw_output.replace("```", "")
                raw_output = raw_output.strip()

            result = json.loads(raw_output)

            return result

        except HfHubHTTPError as e:

            error_text = str(e)

            # Retry temporary 429/model-overloaded errors
            if "429" in error_text or "engine_overloaded" in error_text:

                if attempt < max_retries - 1:

                    wait_time = 2 ** attempt

                    print(
                        f"Hugging Face model busy. "
                        f"Retrying in {wait_time} seconds..."
                    )

                    time.sleep(wait_time)
                    continue

                return {
                    "error": "LLM temporarily unavailable",
                    "details": "Hugging Face model is currently overloaded."
                }

            raise

        except json.JSONDecodeError:

            return {
                "error": "Invalid LLM response",
                "details": "The model did not return valid JSON."
            }

        except Exception as e:

            return {
                "error": "LLM analysis failed",
                "details": str(e)
            }

    return {
        "error": "LLM analysis failed",
        "details": "Maximum retry attempts exceeded."
    }
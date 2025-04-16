import os
import time
from datetime import datetime

from dotenv import load_dotenv
from fastapi import UploadFile
import openai

from .firefly import (
    create_firefly_transaction,
    get_firefly_budgets,
    get_firefly_categories,
)
from .image_utils import process_image
from .models import ReceiptModel

# Load environment variables
load_dotenv()

# Get LLM configuration from environment variables
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL_STRING = os.getenv("LLM_MODEL_STRING")
LLM_API_KEY = os.getenv("LLM_API_KEY")

if not LLM_BASE_URL or not LLM_MODEL_STRING or not LLM_API_KEY:
    raise ValueError("LLM_BASE_URL, LLM_MODEL_STRING, and LLM_API_KEY environment variables must be set")

openai.base_url = LLM_BASE_URL
openai.api_key = LLM_API_KEY


async def extract_receipt_data(file: UploadFile):
    """Extract data from the receipt image without creating a transaction."""
    try:
        print(f"Processing image: {file.filename}")

        # Process the image (resize and compress with more aggressive settings)
        image = await process_image(file, max_size=(768, 768))
        print("Image processed and encoded to base64")

        # Fetch dynamic data from Firefly III
        print("Fetching categories and budgets...")
        categories = get_firefly_categories()
        budgets = get_firefly_budgets()
        print(
            f"Found {len(categories) if categories else 0} categories and {len(budgets) if budgets else 0} budgets"
        )

        # If we couldn't fetch categories or budgets, use default values
        if not categories:
            categories = [
                "Groceries",
                "Dining",
                "Shopping",
                "Transportation",
                "Entertainment",
                "Other",
            ]
            print("Using default categories due to Firefly III connection issues")

        if not budgets:
            budgets = ["Monthly", "Weekly", "Other"]
            print("Using default budgets due to Firefly III connection issues")

        # Construct the prompt.
        receipt_prompt = (
            "Please analyze the attached receipt image and extract the following details: "
            "1) receipt amount, 2) receipt category (choose from: "
            + ", ".join(categories)
            + "), "
            "3) receipt budget (choose from: " + ", ".join(budgets) + "), "
            "4) destination account (store name) "
            "5) date (in YYYY-MM-DD format). Today's date is "
            + datetime.now().strftime("%Y-%m-%d")
            + ". "
            "Most receipts are from the past few days, so use today's date as a reference point when interpreting dates. "
            "If the date is not on the receipt, use today's date as the default."
        )

        # Set a shorter timeout for the API call
        try:
            print("Sending request to LLM for analysis...")
            # Generate receipt details using OpenAI-compatible LLM
            completion = openai.chat.completions.create(
                model=LLM_MODEL_STRING,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts structured receipt data from images."},
                    {"role": "user", "content": [
                        {"type": "text", "text": receipt_prompt},
                        {"type": "image_url", "image_url": f"data:image/jpeg;base64,{image}"}
                    ]}
                ],
                response_format={"type": "json_object"},
                timeout=30
            )
            print("Received response from LLM")
            llm_response = completion.choices[0].message
            # Parse the JSON response into the ReceiptModel (assuming response is in content)
            import json
            parsed = ReceiptModel(**json.loads(llm_response.content))
        except Exception as e:
            print(f"Error during LLM analysis: {str(e)}")
            print(f"Error type: {type(e)}")
            if "timeout" in str(e).lower():
                raise TimeoutError(
                    "The image processing timed out. Please try again with a smaller or clearer image."
                )
            raise e

        # Validate and format the date
        try:
            print(f"Validating date: {parsed.date}")
            # Try to parse the date to ensure it's valid
            date_obj = datetime.strptime(parsed.date, "%Y-%m-%d")
            # Format it back to the expected format
            parsed.date = date_obj.strftime("%Y-%m-%d")
            print("Date validation successful")
        except ValueError:
            # If the date is invalid, use the current date
            print(
                f"Invalid date format: {parsed.date}. Using current date instead."
            )
            parsed.date = datetime.now().strftime("%Y-%m-%d")

        # Return the extracted data as a dictionary
        extracted_data = {
            "date": parsed.date,
            "amount": parsed.amount,
            "store_name": parsed.store_name,
            "category": parsed.category,
            "budget": parsed.budget,
            "available_categories": categories,
            "available_budgets": budgets,
        }
        print("Successfully extracted all data")
        return extracted_data
    except Exception as e:
        print(f"Unexpected error in extract_receipt_data: {str(e)}")
        print(f"Error type: {type(e)}")
        raise


async def create_transaction_from_data(receipt_data, source_account):
    """Create a transaction in Firefly III using the provided data."""
    # Create a ReceiptModel object from the data
    receipt = ReceiptModel(
        date=receipt_data["date"],
        amount=receipt_data["amount"],
        store_name=receipt_data["store_name"],
        category=receipt_data["category"],
        budget=receipt_data["budget"],
    )

    # Implement retry logic with exponential backoff
    max_retries = 3  # Reduced from 5 to 3 to prevent too many duplicates
    retry_delay = 3  # Keep at 3 seconds
    last_error = None

    for attempt in range(max_retries):
        try:
            # Create a transaction based on the receipt data
            transaction_result = create_firefly_transaction(receipt, source_account)

            if transaction_result:
                print("Transaction created successfully:")
                print(f"- Date: {receipt.date}")
                print(f"- Amount: {receipt.amount}")
                print(f"- Store: {receipt.store_name}")
                print(f"- Category: {receipt.category}")
                print(f"- Budget: {receipt.budget}")
                print(f"- Source Account: {source_account}")
                print(f"- Transaction ID: {transaction_result['data']['id']}")
                return f"Transaction created successfully with ID: {transaction_result['data']['id']}"
            else:
                last_error = (
                    "Failed to create transaction. No response from Firefly III."
                )
                print(last_error)

        except Exception as e:
            last_error = str(e)
            print(
                f"Error creating transaction (attempt {attempt + 1}/{max_retries}): {e}"
            )

            # If this is not the last attempt, wait and retry
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2**attempt)  # Exponential backoff
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    # If we've exhausted all retries, return an error message
    error_msg = f"Failed to create transaction after {max_retries} attempts. Last error: {last_error}"
    print(error_msg)
    return error_msg

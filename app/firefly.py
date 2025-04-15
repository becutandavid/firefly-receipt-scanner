import json
import os
from datetime import datetime
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Firefly III configuration
FIREFLY_III_URL = os.getenv("FIREFLY_III_URL")
FIREFLY_III_TOKEN = os.getenv("FIREFLY_III_TOKEN")

# Validate required environment variables
if not FIREFLY_III_TOKEN:
    raise ValueError("FIREFLY_III_TOKEN environment variable is not set")

# Increase timeout for all requests
TIMEOUT = 30  # Increased from 30 to 60 seconds


def get_firefly_categories():
    url = urljoin(FIREFLY_III_URL, "/categories")
    headers = {
        "Authorization": f"Bearer {FIREFLY_III_TOKEN}",
        "Accept": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        categories_data = response.json()["data"]
        return [category["attributes"]["name"] for category in categories_data]
    except requests.exceptions.Timeout:
        print("Request to Firefly III timed out when fetching categories")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching categories: {e}")
        return []


def get_firefly_budgets():
    url = urljoin(FIREFLY_III_URL, "/budgets")
    headers = {
        "Authorization": f"Bearer {FIREFLY_III_TOKEN}",
        "Accept": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        budgets_data = response.json()["data"]
        return [budget["attributes"]["name"] for budget in budgets_data]
    except requests.exceptions.Timeout:
        print("Request to Firefly III timed out when fetching budgets")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching budgets: {e}")
        return []


def get_firefly_asset_accounts():
    url = urljoin(FIREFLY_III_URL, "/accounts")
    headers = {
        "Authorization": f"Bearer {FIREFLY_III_TOKEN}",
        "Accept": "application/json",
    }
    params = {
        "type": "asset"  # Only fetch asset accounts
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        accounts_data = response.json()["data"]
        return [account["attributes"]["name"] for account in accounts_data]
    except requests.exceptions.Timeout:
        print("Request to Firefly III timed out when fetching asset accounts")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching asset accounts: {e}")
        return []


def create_firefly_transaction(receipt, source_account="Cash wallet"):
    url = urljoin(FIREFLY_III_URL, "/transactions")
    headers = {
        "Authorization": f"Bearer {FIREFLY_III_TOKEN}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    # Format the date to ISO 8601 format
    try:
        # Try to parse the date string into a datetime object
        date_obj = datetime.strptime(receipt.date, "%Y-%m-%d")
        # Format it as ISO 8601
        formatted_date = date_obj.strftime("%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        # If parsing fails, try to use the current date
        print(f"Invalid date format: {receipt.date}. Using current date instead.")
        formatted_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")

    payload = {
        "transactions": [
            {
                "type": "withdrawal",
                "date": formatted_date,
                "amount": str(receipt.amount),
                "description": f"Purchase at {receipt.store_name}",
                "destination_name": receipt.store_name,
                "source_name": source_account,
                "category_name": receipt.category,
                "budget_name": receipt.budget,
                "tags": ["automated"],
            }
        ]
    }

    try:
        print(f"Sending transaction to Firefly III: {json.dumps(payload, indent=2)}")
        response = requests.post(url, headers=headers, json=payload, timeout=TIMEOUT)

        # Log response details for debugging
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {response.headers}")

        if response.status_code in [200, 201]:  # Accept both 200 and 201 as success
            return response.json()
        elif response.status_code == 401:
            raise Exception(
                "Authentication failed. Please check your Firefly III API token."
            )
        elif response.status_code == 403:
            raise Exception(
                "You don't have permission to create transactions. Please check your Firefly III permissions."
            )
        elif response.status_code == 404:
            raise Exception(
                "The Firefly III API endpoint was not found. Please check your Firefly III URL."
            )
        elif response.status_code == 422:
            error_data = response.json()
            error_message = "Validation error: "
            if "message" in error_data:
                error_message += error_data["message"]
            else:
                error_message += "Invalid data provided to Firefly III."
            raise Exception(error_message)
        elif response.status_code >= 500:
            raise Exception(
                f"Firefly III server error (HTTP {response.status_code}). The server might be experiencing issues."
            )
        else:
            error_message = f"Error creating transaction: HTTP {response.status_code}"
            try:
                error_data = response.json()
                if "message" in error_data:
                    error_message += f" - {error_data['message']}"
            except Exception:
                error_message += f" - {response.text}"
            raise Exception(error_message)
    except requests.exceptions.Timeout:
        print("Request to Firefly III timed out when creating transaction")
        raise Exception(
            "The request to Firefly III timed out. The server might be experiencing high load or connectivity issues."
        )
    except requests.exceptions.ConnectionError:
        print("Connection error when creating transaction")
        raise Exception(
            "Could not connect to Firefly III. Please check your internet connection and Firefly III URL."
        )
    except requests.exceptions.RequestException as e:
        print(f"Error creating transaction: {e}")
        raise Exception(f"Error communicating with Firefly III: {str(e)}")

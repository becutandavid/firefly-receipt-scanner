import os

from fastapi import (
    FastAPI,
    File,
    Form,
    Request,
    UploadFile,
)
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .firefly import get_firefly_asset_accounts
from .receipt_processing import create_transaction_from_data, extract_receipt_data

app = FastAPI(title="Receipt to Firefly III")

# Add trusted host middleware to handle forwarded headers
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# Create a static directory if it doesn't exist
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Set up templates
templates = Jinja2Templates(directory="app/templates")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve a simple HTML form for uploading receipts."""
    # Fetch asset accounts from Firefly III
    asset_accounts = get_firefly_asset_accounts()

    # If no accounts were fetched, use a default
    if not asset_accounts:
        asset_accounts = ["Cash wallet"]
        print("Using default asset account due to Firefly III connection issues")

    return templates.TemplateResponse(
        "upload.html", {"request": request, "asset_accounts": asset_accounts}
    )


@app.post("/extract")
async def extract_receipt(
    request: Request, file: UploadFile = File(...), source_account: str = Form(...)
):
    try:
        # Process the image and extract data
        extracted_data = await extract_receipt_data(file)

        # Add the source_account to the extracted data
        extracted_data["source_account"] = source_account

        return templates.TemplateResponse(
            "review.html", {"request": request, "extracted_data": extracted_data}
        )
    except TimeoutError:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": "The operation timed out. The image processing is taking too long. Please try again with a smaller or clearer image.",
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            "error.html", {"request": request, "error_message": str(e)}
        )


@app.post("/create-transaction")
async def create_transaction(
    request: Request,
    date: str = Form(...),
    amount: float = Form(...),
    store_name: str = Form(...),
    category: str = Form(...),
    budget: str = Form(...),
    source_account: str = Form(...),
):
    try:
        # Create the transaction
        result = await create_transaction_from_data(
            {
                "date": date,
                "amount": amount,
                "store_name": store_name,
                "category": category,
                "budget": budget,
                "source_account": source_account,
            },
            source_account,
        )

        if result and "Failed to create transaction" in result:
            return templates.TemplateResponse(
                "error.html", {"request": request, "error_message": result}
            )

        return templates.TemplateResponse(
            "upload.html",
            {
                "request": request,
                "asset_accounts": get_firefly_asset_accounts(),
                "success_message": "Transaction created successfully!",
            },
        )
    except Exception as e:
        return templates.TemplateResponse(
            "error.html", {"request": request, "error_message": str(e)}
        )

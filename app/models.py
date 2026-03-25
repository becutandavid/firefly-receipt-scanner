from pydantic import BaseModel


class ReceiptModel(BaseModel):
    date: str
    amount: float
    destination_account: str
    description: str
    category: str
    budget: str

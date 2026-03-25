from datetime import datetime
from dataclasses import dataclass, fields, field

DEFAULT_SYSTEM_PROMPT = """\
You are a helpful assistant that extracts structured receipt data from images.
You return responses as valid json only. Please provide only plaintext json, no code blocks or other formatting.
Use the following json scheme to return data:
@schema
"""

DEFAULT_USER_PROMPT = """\
Please analyze the attached receipt and extract the following details:
1) amount
2) category
3) budget
4) destination account (retailer name)
5) description of the transaction
5) date (in YYYY-MM-DD format)

Most receipts are from the past few days, so use today's date as a reference point when interpreting dates.
If the date is not on the receipt, use today's date as the default.
Today's date is @date.

Please assign a catagory from the following list based on the store name and item types.
[ @catagories ]
If no categories fit, please return an empty string for the field and do not select any categories.

Please assign the budget from the following list based on the store name and item types.
[ @budgets ]
If no budget fits, please return an empty string for the field and do not select any budget.
"""

@dataclass
class PromptComponents:
    date: str = datetime.now().strftime("%Y-%m-%d")
    catagories: list[str] = field(default_factory=list)
    budgets: list[str] = field(default_factory=list)
    schema: str = ""

class PromptConstructor():
    def __init__(self, system_prompt=DEFAULT_SYSTEM_PROMPT, user_prompt=DEFAULT_USER_PROMPT):
        self.system_prompt = system_prompt if system_prompt else ""
        self.user_prompt = user_prompt if user_prompt else ""

    def get_system_prompt(self, components: PromptComponents = PromptComponents()) -> str:
        return self.construct_prompt(self.system_prompt, components)
    
    def get_user_prompt(self, components: PromptComponents = PromptComponents()) -> str:
        return self.construct_prompt(self.user_prompt, components)

    def construct_prompt(self, base_prompt: str, components: PromptComponents = PromptComponents()) -> str:
        prompt = base_prompt

        for field in fields(components):
            value = getattr(components, field.name)
            tag = f"@{field.name}"
            if value:
                if isinstance(value, set) or isinstance(value, list):
                    value = ", ".join(value)
            else:
                value = ""

            prompt = prompt.replace(tag, value)

        return prompt
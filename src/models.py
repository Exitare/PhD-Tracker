from pydantic import BaseModel

class Milestone(BaseModel):
    milestone: str
    due_date: str



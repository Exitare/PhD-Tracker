from pydantic import BaseModel

class AIMilestone(BaseModel):
    milestone: str
    due_date: str



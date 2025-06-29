from pydantic import BaseModel


class AIMilestone(BaseModel):
    milestone: str
    due_date: str
    id: int | None = None

    def __str__(self):
        return f"Milestone: {self.milestone}, Due Date: {self.due_date}, ID: {self.id}"

    def to_json(self):
        return {
            "milestone": self.milestone,
            "due_date": self.due_date,
            "id": self.id
        }

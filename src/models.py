from pydantic import BaseModel
from typing import Optional


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


class AIJournalRecommendation(BaseModel):

    name: str
    scope: str
    impact_factor: Optional[float]
    open_access: bool
    link: str

    def __str__(self):
        return f"Journal: {self.name}, Scope: {self.scope}, Impact Factor: {self.impact_factor}, Open Access: {self.open_access}, Link: {self.link}"

    def to_json(self):
        return {
            "name": self.name,
            "scope": self.scope,
            "impact_factor": self.impact_factor,
            "open_access": self.open_access,
            "link": self.link
        }
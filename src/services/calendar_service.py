from ics import Calendar, Event
from datetime import datetime
from src.db.models import Milestone
from typing import List


class CalendarService:

    @staticmethod
    def generate_milestones_ics(milestones: List[Milestone]) -> Calendar:
        """
        Create a calendar object from a list of milestones.

        Parameters:
            milestones (list): List of dicts with 'title' and 'date' keys.
                               Example: [{'title': 'Proposal', 'date': '2025-07-10'}, ...]

        Returns:
            ics.Calendar: The calendar object with added events.
        """
        calendar = Calendar()

        for milestone in milestones:
            event = Event()
            event.name = milestone.milestone
            event.begin = datetime.strptime(milestone.due_date, "%Y-%m-%d").date()
            event.make_all_day()
            calendar.events.add(event)

        return calendar

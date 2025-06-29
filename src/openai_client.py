from datetime import datetime, timezone
from openai import OpenAI
import json, re, os
from .models import AIMilestone
from src.db.models import Milestone
from typing import List, Tuple, Dict, Any
from dotenv import load_dotenv
from datetime import date

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_KEY"))
model: str = os.environ.get("OPENAI_MODEL")
METER_NAME: str = "tokenrequests"


class OpenAIService:

    @staticmethod
    def generate_reviewer_reply(reviewer_text: str) -> str:
        reply_prompt = f"""You are a scientific writing assistant. 
        Based on the following reviewer feedback, generate a polite and structured response to each point, assuming the author agrees to revise:

        Reviewer Comments:
        {reviewer_text}

        Respond point-by-point with a heading for each reviewer (e.g., Reviewer 1, Reviewer 2)  if available."""

        # Generate polite response
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": reply_prompt}
            ],
            temperature=0.7
        )

        return response.choices[0].message.content.strip()

    @staticmethod
    def submit_reviewer_feedback_milestone_generation(reviewer_text: str, deadline: str) -> Tuple[
        List[AIMilestone], Dict[str, Any]]:
        current_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        milestone_prompt = f"""You are a scientific writer.
        Based on the following reviewer feedback, generate a revision plan with 5-7 concrete milestones with recommended due dates before {deadline}. 
        Return only raw JSON as a list of objects with fields: milestone, due_date (YYYY-MM-DD).
        Do not include explanations or markdown.

        Reviewer Comments:
        {reviewer_text}
        """

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are a helpful assistant that generates academic milestones. Always return raw JSON, "
                        f"never explanations or markdown. The json should contain the fields: milestone, due_date. "
                        f"The current day is {current_day}."
                    )
                },
                {"role": "user", "content": milestone_prompt}
            ],
            temperature=0.7
        )

        content = response.choices[0].message.content.strip()

        try:
            # Clean up markdown or code blocks if present
            if content.startswith("```"):
                content = re.sub(r"```(?:json)?", "", content).strip("` \n")

            raw_data = json.loads(content)
            milestones = [AIMilestone(**m) for m in raw_data]

            usage = response.usage.model_dump() if hasattr(response.usage, 'model_dump') else dict(response.usage)

            return milestones, usage

        except Exception as e:
            print("Error parsing reviewer feedback milestones:", e)
            print("Raw content:\n", content)
            return [], {"error": str(e), "raw_content": content}

    @staticmethod
    def refine_milestones(project_description: str, subproject_description: str, milestones: List[Milestone],
                          additional_user_context: str, deadline: str) -> Tuple[
        List[AIMilestone], Dict[str, Any]]:

        print(milestones)
        prompt = f"""
        I am working on a project with the following description: "{project_description}".
        This is my subproject description: "{subproject_description}".
        I have the following milestones to achieve by {deadline}:
        {json.dumps([m.to_json() for m in milestones], indent=2)}
        Please refine these milestones based on the following additional context: "{additional_user_context}".
        Return only raw JSON as a list of objects with fields: id, milestone, due_date (YYYY-MM-DD), where the ID is the original milestone ID.
        Do not include explanations or markdown.
        Make sure the due dates are realistic and achievable and do not exceed the deadline.
        Additionally, if milestone dates are already in the past, do NOT change them. Also if a milestone is already completed, do not change it.
        if necessary you can create new milestones with increasing ID number, but only use that if absolutely necessary. Dont mix tasks together.
        It is not great to have a milestone that is Write Chapter 1 and get feedback at the same time, so please split those tasks if needed.
        """

        current_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a helpful assistant that refines academic milestones. Always return raw JSON, "
                               f"never explanations or markdown. The json should contain the fields: milestone, due_date. The current day is {current_day}."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        content = response.choices[0].message.content.strip()

        try:
            # Clean up markdown if needed
            if content.startswith("```"):
                content = re.sub(r"```(?:json)?", "", content).strip("` \n")

            raw_data = json.loads(content)
            refined_milestones = [AIMilestone(**m) for m in raw_data]

            usage = response.usage.model_dump() if hasattr(response.usage, 'model_dump') else dict(response.usage)

            return refined_milestones, usage
        except Exception as e:
            print("Error parsing refined milestones:", e)
            print("Raw content:\n", content)
            return [], {"error": str(e), "raw_content": content}

    @staticmethod
    def generate_milestones(goal: str, deadline: str) -> Tuple[List[AIMilestone], Dict[str, Any]]:
        prompt = f"""
        I want to achieve the following academic goal: "{goal}" by {deadline}.
        Break this into ONlY 5-7 concrete milestones with recommended due dates. 
        Return only raw JSON as a list of objects with fields: milestone, due_date (YYYY-MM-DD).
        Do not include explanations or markdown.
        """

        current_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a helpful assistant that generates academic milestones. Always return raw JSON, "
                               f"never explanations or markdown. The json should contain the fields: milestone, due_date. The curernt day is {current_day}."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        content = response.choices[0].message.content.strip()

        try:
            # Clean up markdown if needed
            if content.startswith("```"):
                content = re.sub(r"```(?:json)?", "", content).strip("` \n")

            raw_data = json.loads(content)
            milestones = [AIMilestone(**m) for m in raw_data]

            # Extract token usage
            usage = response.usage.model_dump() if hasattr(response.usage, 'model_dump') else dict(response.usage)

            return milestones, usage
        except Exception as e:
            print("Error parsing milestones:", e)
            print("Raw content:\n", content)
            return [], {"error": str(e), "raw_content": content}

from datetime import datetime, timezone
from openai import OpenAI
import json, re, os
from .models import AIMilestone
from typing import List
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_KEY"))


def generate_milestones(goal: str, deadline: str) -> List[AIMilestone]:
    prompt = f"""
    I want to achieve the following academic goal: "{goal}" by {deadline}.
    Break this into ONlY 5-7 concrete milestones with recommended due dates. 
    Return only raw JSON as a list of objects with fields: milestone, due_date (YYYY-MM-DD).
    Do not include explanations or markdown.
    """

    current_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    response = client.chat.completions.create(
        model="gpt-4o",
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
        return [AIMilestone(**m) for m in raw_data]
    except Exception as e:
        print("Error parsing milestones:", e)
        print("Raw content:\n", content)
        return []

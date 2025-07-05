from datetime import datetime, timezone
from openai import OpenAI
import json, re, os
from src.models import AIMilestone, AIJournalRecommendation
from src.db.models import Milestone
from typing import List, Tuple, Dict, Any
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.environ.get("OPENAI_KEY"))
model: str = os.environ.get("OPENAI_MODEL")
METER_NAME: str = "tokenrequests"


class OpenAIService:
    @staticmethod
    def get_poster_requirements(conference_name: str) -> Tuple[str, Dict[str, Any]]:
        prompt = """
        You are an expert assistant trained to extract poster submission deadlines and session times for this conference:""" + conference_name + """

Your task is to search the official conference website or official call for abstracts page and return ONLY verified, current data for the year """ + datetime.now().strftime("%B %d, %Y") + """.
Do not include outdated information from last year or any other year.
Conference Name: """ + conference_name + """
Return data ONLY IF you find it clearly and explicitly stated on an official source (conference website, program PDF, or call for abstracts). Do not guess or use outdated sources.

Return exactly one JSON object in this format:

{
  "abstract_submission_due": "e.g. 'Friday, March 7, 2025'",
  "final_submission_due": "e.g. 'Friday, March 21, 2025'",
  "poster_networking_hours": "e.g. 'Monday, March 24, 2025, 2:00 PM - 4:00 PM'",
  "source_url": "Direct URL to the official source where the above data was found"
}

Do not return anything other than the JSON.
         """
        print(prompt)
        response = client.chat.completions.create(
            model='gpt-4.1',
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )

        content = response.choices[0].message.content.strip()

        print(content)

        try:
            # Ensure it's proper JSON even if it's wrapped in string accidentally
            requirements = json.loads(content)
        except json.JSONDecodeError as e:
            print(content)
            raise ValueError(f"Failed to parse JSON response: {e}\nRaw content:\n{content}")

        # Extract token usage
        usage = (
            response.usage.model_dump()
            if hasattr(response.usage, "model_dump")
            else dict(response.usage)
            if response.usage else {}
        )

        return requirements, usage

    @staticmethod
    def get_journal_requirements(journal_name: str) -> Tuple[str, Dict[str, Any]]:
        prompt = """
        You are an expert assistant trained to extract manuscript submission requirements for scientific journals. 
        Given the name of a journal, your task is to:
        1. Search the web to locate the official “Guide to Authors” or equivalent manuscript submission instructions.
        2. Extract the submission requirements and return them in the structured JSON format below.

        ⚠️ Only include verified and directly stated requirements from the official guidelines. 
        If a detail is not found or unclear, set its value to null, false, or an empty string, depending on the field.

        Journal Name: """ + journal_name + """

        Return only raw JSON with the following fields (no Markdown code blocks):
        {
          "article_types": [],
          "initial_submission": {
            "format": "",
            "figures": "",
            "line_numbers": false,
            "figure_legends": "",
            "reference_list_with_titles": false
          },
          "title_and_abstract": {
            "title": {
              "max_length_characters": null,
              "max_length_words": null,
              "requirements": ""
            },
            "abstract": {
              "length_words": null,
              "type": ""
            }
          },
          "main_text": {
            "flexibility": "",
            "length_words": {
              "max": null
            },
            "figures_or_tables": {
              "max": null
            },
            "references": {
              "max": null,
              "methods_references_excluded": false
            }
          },
          "methods_section": {
            "replicability_required": false,
            "length_words": {
              "suggested_max": null
            },
            "detailed_protocols": "",
            "references_not_counted": false
          },
          "figures_and_tables": {
            "initial_submission": {
              "resolution": "",
              "format": ""
            },
            "final_submission": {
              "resolution_dpi": null,
              "color_mode": "",
              "fonts": "",
              "format": ""
            },
            "tables": {
              "title_required": false,
              "footnotes_required": false,
              "page_fit_required": false
            }
          },
          "references": {
            "titles_required": false,
            "numbering": "",
            "main_text_limit": null,
            "methods_exempt": false
          },
          "end_matter": {
            "author_contributions": false,
            "competing_interests": false,
            "data_availability_statement": false,
            "code_availability_statement": false,
            "acknowledgements": "",
            "materials_correspondence": ""
          },
          "statistics_and_reporting": {
            "tests_described": false,
            "error_bars_defined": false,
            "n_values_reported": false,
            "p_values_and_test_stats_reported": false,
            "reporting_summary_required_for_life_sciences": false
          },
          "submission_checklist": [],
          "source_url": ""
        }
        """

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )

        content = response.choices[0].message.content.strip()

        try:
            # Ensure it's proper JSON even if it's wrapped in string accidentally
            requirements = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}\nRaw content:\n{content}")

        # Extract token usage
        usage = (
            response.usage.model_dump()
            if hasattr(response.usage, "model_dump")
            else dict(response.usage)
            if response.usage else {}
        )

        return requirements, usage

    @staticmethod
    def generate_journal_recommendations(project_description: str) -> Tuple[
        List[AIJournalRecommendation], Dict[str, Any]]:
        # TODO: Add option for users to increase or decrease amount of journals returned
        prompt = f"""You are a helpful assistant that recommends academic journals.
        Based on the following project description, recommend 6 suitable journals for publication.
        Provide the journal name, a brief description, and a link to the journal's website.

        Project Description:
        {project_description}

        Return only raw JSON as a list of objects with the following fields:
        - name (string)
        - scope (string)
        - impact_factor (float or null)
        - open_access (true or false)
        - link (string)

        Do not include explanations or markdown. Do not make information up — verify the journal names and links.

        Example:
        [
            {{
                "name": "Open Access AI Journal",
                "scope": "Artificial intelligence and machine learning",
                "impact_factor": 3.8,
                "open_access": true,
                "link": "https://example.com/journal3"
            }}
        ]
        """

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )

        content = response.choices[0].message.content.strip()

        try:
            if content.startswith("```"):
                content = re.sub(r"```(?:json)?", "", content).strip("` \n")

            content = content.strip()
            if not content.startswith("["):
                raise ValueError("Expected JSON list as output.")

            raw_data = json.loads(content)
            recommendations: List[AIJournalRecommendation] = [AIJournalRecommendation(**r) for r in raw_data]
            recommendations = [r for r in recommendations if r.impact_factor is not None]

            usage = response.usage.model_dump() if hasattr(response.usage, 'model_dump') else dict(response.usage)

            return recommendations, usage

        except Exception as e:
            print("Error parsing journal recommendations:", e)
            print("Raw content:\n", content)
            return [], {"error": str(e), "raw_content": content}

    @staticmethod
    def generate_reviewer_reply(reviewer_text: str) -> str:
        # TODO: FIX and return usage
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
    def submit_reviewer_feedback_milestone_generation(reviewer_text: str, additional_context: str, deadline: str) -> \
            Tuple[
                List[AIMilestone], Dict[str, Any]]:
        current_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        milestone_prompt = f"""You are a scientific writer.
        Based on the following reviewer feedback, generate a revision plan with 5-7 concrete milestones with recommended due dates before {deadline}. 
        Return only raw JSON as a list of objects with fields: milestone, due_date (YYYY-MM-DD).
        Do not include explanations or markdown.

        Reviewer Comments:
        {reviewer_text}
        """

        if additional_context:
            milestone_prompt += f"\nAdditional context: {additional_context}"

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

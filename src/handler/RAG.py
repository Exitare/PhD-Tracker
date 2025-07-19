from langchain_community.chat_models import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.utilities import SerpAPIWrapper
import json
import os
import logging
from src.db.models import Project
from src import get_db_session
from flask import flash
import re


class RAGHandler:

    @staticmethod
    def journal_requirements() -> bool:
        return json.loads("""{
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
        }""")

    @staticmethod
    def extract_venue_requirements(project_id: int, user_id: int, venue_name: str) -> bool:
        db_session = get_db_session()
        project: Project = db_session.query(Project).filter_by(id=project_id).first()

        if not project:
            flash("Project not found.", "danger")
            return False

        if project.user_id != user_id:
            flash("You do not have permission to access this project.", "danger")
            return False

        os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_KEY")
        serp_key = os.environ.get("SERPAPI_KEY")

        if not serp_key:
            flash("Missing SerpAPI key.", "danger")
            return False

        if not project:
            flash("Project not found.", "danger")
            return False

        if project.type not in ['poster', 'paper']:
            flash("Unsupported project type.", "danger")
            return False

        # Step 1: Search
        search = SerpAPIWrapper(serpapi_api_key=serp_key)
        search_query = f"Conference submission requirements for {venue_name} 2025" if project.type == "poster" \
            else f"Journal submission requirements for {venue_name}"

        try:
            search_results = search.results(search_query)
            urls = [r["link"] for r in search_results.get("organic_results", [])[:3]]
            logging.info(f"Search results: {urls}")
        except Exception as e:
            flash(f"Search failed: {str(e)}", "danger")
            return False

        if not urls:
            flash("No sources found for venue requirements.", "danger")
            return False

        # Step 2: Load content
        documents = []
        for url in urls:
            try:
                docs = WebBaseLoader(url).load()
                documents.extend(docs)
            except Exception as e:
                logging.warning(f"[!] Failed to load {url}: {e}")

        if not documents:
            flash("Failed to retrieve any usable content from top URLs.", "danger")
            return False

        # Step 3: Embedding + Retrieval
        embeddings = OpenAIEmbeddings()
        vectorstore = FAISS.from_documents(documents, embeddings)

        qa = RetrievalQA.from_chain_type(
            llm=ChatOpenAI(model="gpt-4.1"),
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
            return_source_documents=True
        )

        json_format = (
            """{\n  "abstract_submission_due": "",\n 
                    "fee": "",\n
                    "character_limit": "",\n
                    "conference_url": "",\n
                    "poster_networking_hours": "",\n
                }"""
        ) if project.type == "poster" else RAGHandler.journal_requirements()

        if project.type == "poster":
            prompt = (
                f"What are the {project.type} submission requirements for {venue_name}?\n"
                f"Return the answer strictly as minified JSON. Use only double quotes and no trailing commas. "
                f"Do not include any explanation. Respond with only the JSON body.\n"
                f"Here is the expected format:\n{json.dumps(json_format) if isinstance(json_format, dict) else json_format}"
                f"Please search specifically for answers for the json attributes."
            )
        else:
            prompt = (
                f"What are the {project.type} submission requirements for {venue_name}?\n"
                f"Return the answer strictly as minified JSON. Use only double quotes and no trailing commas. "
                f"Do not include any explanation. Respond with only the JSON body.\n"
                f"Here is the expected format:\n{json.dumps(json_format)}"
            )

        response = qa.invoke({"query": prompt})
        try:
            json_string = response['result']
            print("GPT raw result:\n", json_string)  # optional debugging

            # Strip any non-JSON text before/after the main body
            match = re.search(r'({.*})', json_string, re.DOTALL)
            if not match:
                raise ValueError("No JSON found in model response.")

            clean_json = match.group(1)
            parsed = json.loads(clean_json)

            project.venue_requirements_data = parsed
            db_session.commit()
            return True
        except json.JSONDecodeError as e:
            logging.error(f"[!] JSON decode error: {e}\nResponse was: {response['result']}")
        except Exception as e:
            logging.error(f"Error processing venue requirements: {e}")
        db_session.rollback()
        return False

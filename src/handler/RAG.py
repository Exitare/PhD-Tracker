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


class RAGHandler:

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
            llm=ChatOpenAI(),
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
            return_source_documents=True
        )

        json_format = (
                """{\n  "abstract_submission_due": "",\n  "final_submission_due": "",\n"""
                + ('  "poster_networking_hours": "",\n' if project.type == "poster" else "")
                + '  "source_url": ""\n}'
        )

        prompt = (
            f"What are the {project.type} submission requirements for {venue_name}?\n"
            f"Return the answer strictly in this JSON format:\n{json_format}"
        )

        try:
            response = qa.invoke({"query": prompt})
            parsed = json.loads(response['result'])

            project.venue_requirements_data = parsed
            print(project.venue_requirements)
            print("Successfully processed venue requirements:", parsed)

            db_session.commit()
            return True
        except Exception as e:
            logging.error(f"Error processing venue requirements: {e}")
            db_session.rollback()
            return False
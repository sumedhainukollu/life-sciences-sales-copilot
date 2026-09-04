"""
generate_call_prep.py
-----------------------
The "G" (generation) in RAG. Retrieves the most relevant trial + rep-note
documents for a given HCP/drug/condition, then asks Gemini to draft
a structured call prep sheet grounded in that retrieved context.
"""

import os
from google import genai
from dotenv import load_dotenv

from src.vectorstore import query as vector_query
from src.prompts import SYSTEM_PROMPT, build_user_prompt

load_dotenv()

GEMINI_MODEL = "gemini-3.6-flash"


def _get_client():
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY not set. Add your key to the .env file."
        )

    return genai.Client(api_key=api_key)


def retrieve_context(
    hcp_name: str,
    drug: str,
    condition: str,
    n_results: int = 8
) -> tuple[str, list, list]:
    """
    Retrieve relevant clinical trial records and prior rep notes.

    Returns:
        retrieved_context: formatted text sent to Gemini
        trial_hits: retrieved clinical trial documents
        note_hits: retrieved rep-note documents
    """

    trial_query = f"{drug} {condition} clinical trial efficacy safety dosing"
    note_query = f"{hcp_name} {drug} notes concerns questions"

    trial_hits = vector_query(
        trial_query,
        n_results=n_results,
        where={"source_type": "clinical_trial"}
    )

    note_hits = vector_query(
        note_query,
        n_results=n_results,
        where={
            "source_type": "rep_note",
            "hcp_name": hcp_name
        }
    )
    context_parts = []

    if trial_hits:
        context_parts.append("### Clinical Trial Records ###")
        context_parts.extend(h["text"] for h in trial_hits)

    if note_hits:
        context_parts.append("### Prior Rep Call Notes ###")
        context_parts.extend(h["text"] for h in note_hits)

    if not context_parts:
        retrieved_context = "No matching source documents found in the index."
    else:
        retrieved_context = "\n\n".join(context_parts)

    return retrieved_context, trial_hits, note_hits


def generate_call_prep_sheet(
    hcp_name: str,
    drug: str,
    condition: str,
    extra_context: str = ""
) -> tuple[str, list, list]:

    retrieved, trial_hits, note_hits = retrieve_context(
        hcp_name,
        drug,
        condition
    )

    user_prompt = build_user_prompt(
        hcp_name,
        drug,
        condition,
        extra_context,
        retrieved
    )

    client = _get_client()

    prompt = f"""
{SYSTEM_PROMPT}

{user_prompt}
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    return response.text, trial_hits, note_hits


if __name__ == "__main__":
    sheet, trial_hits, note_hits = generate_call_prep_sheet(
        hcp_name="Dr. Maria Chen",
        drug="pembrolizumab",
        condition="non-small cell lung cancer",
        extra_context="Upcoming lunch-and-learn, 15 minutes only.",
    )

    print(sheet)

    print("\n\n===== RETRIEVED CLINICAL TRIAL SOURCES =====")
    for hit in trial_hits:
        print(hit["text"])

    print("\n\n===== RETRIEVED REP NOTE SOURCES =====")
    for hit in note_hits:
        print(hit["text"])
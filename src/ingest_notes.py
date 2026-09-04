"""
ingest_notes.py
----------------
Loads rep call notes from a CSV (this is what you'd normally export from a
CRM like Veeva or Salesforce Life Sciences Cloud) and converts each row
into a text "document" for the RAG index.
x
Expected CSV columns:
    hcp_name, hcp_specialty, institution, date, drug, topic, note_text
"""

import pandas as pd
from typing import List, Dict


def get_note_documents(csv_path: str) -> List[Dict]:
    df = pd.read_csv(csv_path)
    required_cols = {"hcp_name", "date", "drug", "topic", "note_text"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"rep notes CSV is missing required columns: {missing}")

    docs = []
    for i, row in df.iterrows():
        text = (
            f"Rep call note — HCP: {row.get('hcp_name')} "
            f"({row.get('hcp_specialty', 'Specialty not provided')}, "
            f"{row.get('institution', 'Institution not provided')})\n"
            f"Date: {row.get('date')}\n"
            f"Drug discussed: {row.get('drug')}\n"
            f"Topic: {row.get('topic')}\n"
            f"Note: {row.get('note_text')}"
        )
        docs.append({
            "id": f"note-{i}",
            "source_type": "rep_note",
            "hcp_name": row.get("hcp_name"),
            "drug": row.get("drug"),
            "topic": row.get("topic"),
            "date": str(row.get("date")),
            "text": text,
        })
    return docs


if __name__ == "__main__":
    docs = get_note_documents("data/rep_notes_example.csv")
    for d in docs:
        print("=" * 80)
        print(d["text"])

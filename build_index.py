"""
build_index.py
----------------
Run this once (and again any time you want to refresh data) to pull
clinical trial data + rep notes and load them into the local vector index.

Usage examples:
    python build_index.py --drug "pembrolizumab" --condition "non-small cell lung cancer"
    python build_index.py --drug "Drug X" --condition "NSCLC" --notes data/rep_notes_example.csv
    python build_index.py --reset --drug "Drug X" --condition "NSCLC"
"""

import argparse
from src.ingest_trials import get_trial_documents
from src.ingest_notes import get_note_documents
from src.vectorstore import add_documents, reset_collection


def main():
    parser = argparse.ArgumentParser(description="Build the Life Sciences Sales Copilot index.")
    parser.add_argument("--drug", type=str, default=None, help="Drug / compound / intervention name")
    parser.add_argument("--condition", type=str, default=None, help="Condition / indication")
    parser.add_argument("--notes", type=str, default="data/rep_notes_example.csv",
                         help="Path to rep notes CSV")
    parser.add_argument("--max-studies", type=int, default=15)
    parser.add_argument("--reset", action="store_true", help="Wipe the existing index first")
    args = parser.parse_args()

    if args.reset:
        reset_collection()

    if args.drug or args.condition:
        print(f"Fetching trials for drug='{args.drug}' condition='{args.condition}'...")
        trial_docs = get_trial_documents(drug=args.drug, condition=args.condition,
                                          max_studies=args.max_studies)
        print(f"Fetched {len(trial_docs)} trials from ClinicalTrials.gov.")
        add_documents(trial_docs)
    else:
        print("No --drug or --condition given, skipping trial ingestion.")

    if args.notes:
        print(f"Loading rep notes from {args.notes}...")
        note_docs = get_note_documents(args.notes)
        print(f"Loaded {len(note_docs)} rep notes.")
        add_documents(note_docs)

    print("Index build complete.")


if __name__ == "__main__":
    main()

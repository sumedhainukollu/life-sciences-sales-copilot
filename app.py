"""
app.py
-------
Streamlit front-end for the Life Sciences Sales Copilot.

Run with:  streamlit run app.py
"""

import streamlit as st
from src.ingest_trials import get_trial_documents
from src.ingest_notes import get_note_documents
from src.vectorstore import add_documents
from src.generate_call_prep import generate_call_prep_sheet

st.set_page_config(page_title="Life Sciences Sales Copilot", page_icon="🧬", layout="centered")

st.title(" Life Sciences Sales Copilot")
st.caption("RAG-powered HCP call prep, grounded in ClinicalTrials.gov data + your call notes.")

with st.expander("Step 1 — Index data (run once per drug/condition you care about)", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        idx_drug = st.text_input("Drug / compound", value="Drug X")
    with col2:
        idx_condition = st.text_input("Condition / indication", value="")
    notes_path = st.text_input("Rep notes CSV path", value="data/rep_notes_example.csv")

    if st.button("Build / refresh index"):
        with st.spinner("Pulling trial data and indexing..."):
            try:
                trial_docs = get_trial_documents(drug=idx_drug or None, condition=idx_condition or None)
                add_documents(trial_docs)
                note_docs = get_note_documents(notes_path)
                add_documents(note_docs)
                st.success(f"Indexed {len(trial_docs)} trials and {len(note_docs)} rep notes.")
            except Exception as e:
                st.error(f"Indexing failed: {e}")

st.divider()
st.subheader("Step 2 — Generate a call prep sheet")

hcp_name = st.text_input("HCP name", value="Dr. Maria Chen")
drug = st.text_input("Drug / compound under discussion", value="Drug X")
condition = st.text_input("Condition / indication", value="non-small cell lung cancer")
extra_context = st.text_area("Anything else about this call?", placeholder="e.g. 15-minute lunch meeting, follow-up on prior safety question...")

if st.button("Generate call prep sheet", type="primary"):
    with st.spinner("Retrieving context and drafting with Gemini..."):
        try:
            sheet, trial_hits, note_hits = generate_call_prep_sheet(
                hcp_name,
                drug,
                condition,
                extra_context
            )

            st.markdown(sheet)


            st.subheader("Sources Used")

            if trial_hits:
                st.markdown("**Clinical Trial Sources**")

                for hit in trial_hits:
                    text = hit["text"]

                    # Extract the first line containing the trial identifier
                    trial_line = next(
                        (line for line in text.splitlines() if line.startswith("Trial:")),
                        "Clinical trial source"
                    )

                    # Extract status and phase
                    status_line = next(
                        (line for line in text.splitlines() if line.startswith("Status:")),
                        ""
                    )

                    st.markdown(
                        f"- **{trial_line.replace('Trial: ', '')}**  \n"
                        f"  {status_line}"
                    )

            if note_hits:
                st.markdown("**Rep Note Sources**")

                for hit in note_hits:
                    text = hit["text"]

                    hcp_line = next(
                        (line for line in text.splitlines() if line.startswith("Rep call note")),
                        "Rep call note"
                    )

                    date_line = next(
                        (line for line in text.splitlines() if line.startswith("Date:")),
                        ""
                    )

                    topic_line = next(
                        (line for line in text.splitlines() if line.startswith("Topic:")),
                        ""
                    )

                    st.markdown(
                        f"- **{hcp_line.replace('Rep call note — ', '')}**  \n"
                        f"  {date_line} | {topic_line}"
                    )

            if not trial_hits and not note_hits:
                st.info("No source documents were retrieved.")


            st.download_button(
                "Download as Markdown",
                sheet,
                file_name=f"call_prep_{hcp_name.replace(' ', '_')}.md"
            )

        except Exception as e:
            st.error(f"Generation failed: {e}")
st.divider()
st.caption(
    "⚠️ Internal sales-enablement prep tool only. All claims are grounded in retrieved "
    "ClinicalTrials.gov data and internal rep notes. This output has NOT been through "
    "Medical/Legal/Regulatory (MLR) review and must not be shared externally as-is."
)

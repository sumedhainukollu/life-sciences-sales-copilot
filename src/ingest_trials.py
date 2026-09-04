"""
ingest_trials.py
-----------------
Pulls structured clinical trial data from the official ClinicalTrials.gov
API (v2) for a given drug/compound and/or condition, and turns each trial
into a clean text "document" that we can later embed and search over.

API docs: https://clinicaltrials.gov/data-api/api
No API key is required for this API.
"""

import requests
from typing import List, Dict, Optional

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"


def fetch_trials(
    drug: Optional[str] = None,
    condition: Optional[str] = None,
    max_studies: int = 15,
) -> List[Dict]:
    """
    Query ClinicalTrials.gov for studies matching a drug/intervention name
    and/or a condition (indication). Returns raw JSON study records.
    """
    if not drug and not condition:
        raise ValueError("Provide at least a drug name or a condition.")

    params = {
        "format": "json",
        "pageSize": max_studies,
        # ClinicalTrials.gov API v2 field-specific search syntax:
        # AREA[InterventionName] / AREA[ConditionSearch] etc. can also be used,
        # but the simple query.intr / query.cond params below are the
        # documented, easier-to-use shortcuts.
    }
    if drug:
        params["query.intr"] = drug
    if condition:
        params["query.cond"] = condition

    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("studies", [])


def _get(d: Dict, *path, default="Not reported"):
    """Safely walk a nested dict."""
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur if cur not in (None, "", []) else default


def study_to_document(study: Dict) -> Dict:
    """
    Convert one raw ClinicalTrials.gov study JSON object into a compact
    dict with the fields a sales rep / MSL actually cares about, plus a
    single 'text' blob that's ready to be embedded for RAG.
    """
    protocol = study.get("protocolSection", {})

    nct_id = _get(protocol, "identificationModule", "nctId")
    title = _get(protocol, "identificationModule", "briefTitle")
    official_title = _get(protocol, "identificationModule", "officialTitle")

    status = _get(protocol, "statusModule", "overallStatus")
    phase_list = _get(protocol, "designModule", "phases", default=[])
    phase = ", ".join(phase_list) if isinstance(phase_list, list) and phase_list else "Not reported"

    conditions = _get(protocol, "conditionsModule", "conditions", default=[])
    conditions_str = ", ".join(conditions) if isinstance(conditions, list) else str(conditions)

    interventions_raw = _get(protocol, "armsInterventionsModule", "interventions", default=[])
    interventions = [i.get("name", "") for i in interventions_raw if isinstance(i, dict)]
    interventions_str = ", ".join([i for i in interventions if i]) or "Not reported"

    summary = _get(protocol, "descriptionModule", "briefSummary")

    eligibility = _get(protocol, "eligibilityModule", "eligibilityCriteria")
    min_age = _get(protocol, "eligibilityModule", "minimumAge")
    max_age = _get(protocol, "eligibilityModule", "maximumAge")
    sex = _get(protocol, "eligibilityModule", "sex")

    sponsor = _get(protocol, "sponsorCollaboratorsModule", "leadSponsor", "name")

    outcomes_raw = _get(protocol, "outcomesModule", "primaryOutcomes", default=[])
    outcomes = [o.get("measure", "") for o in outcomes_raw if isinstance(o, dict)]
    outcomes_str = "; ".join([o for o in outcomes if o]) or "Not reported"

    enrollment = _get(protocol, "designModule", "enrollmentInfo", "count")

    start_date = _get(protocol, "statusModule", "startDateStruct", "date")
    completion_date = _get(protocol, "statusModule", "completionDateStruct", "date")

    text = f"""Trial: {nct_id} — {title}
Official title: {official_title}
Status: {status} | Phase: {phase}
Sponsor: {sponsor}
Conditions studied: {conditions_str}
Interventions: {interventions_str}
Enrollment (planned/actual): {enrollment}
Start date: {start_date} | Completion date: {completion_date}
Primary outcome measure(s): {outcomes_str}
Eligibility: Sex={sex}, Age {min_age} to {max_age}
Brief summary: {summary}
Eligibility criteria (excerpt): {str(eligibility)[:800]}
""".strip()

    return {
        "id": nct_id,
        "source_type": "clinical_trial",
        "nct_id": nct_id,
        "phase": phase,
        "status": status,
        "drug": interventions_str,
        "condition": conditions_str,
        "text": text,
    }


def get_trial_documents(drug: Optional[str] = None, condition: Optional[str] = None,
                         max_studies: int = 15) -> List[Dict]:
    """Fetch + convert in one call. This is the function other modules import."""
    raw_studies = fetch_trials(drug=drug, condition=condition, max_studies=max_studies)
    return [study_to_document(s) for s in raw_studies]


if __name__ == "__main__":
    # Quick manual test:
    #   python src/ingest_trials.py
    docs = get_trial_documents(drug="pembrolizumab", condition="non-small cell lung cancer", max_studies=5)
    for d in docs:
        print("=" * 80)
        print(d["text"])

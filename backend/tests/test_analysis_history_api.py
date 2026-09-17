"""Phase 11: authenticated analysis-history endpoints.

GET /api/analyses (paginated list) and GET /api/analyses/{analysis_id}
(full detail), through the live HTTP API with real registered users -
mirrors tests/test_ownership.py's approach. The two hard rules under
test throughout: ownership is derived ONLY from the caller's own JWT
(never a client-supplied id), and neither endpoint ever reruns the
deterministic/semantic matcher - everything returned must already be
sitting in PostgreSQL from a prior POST /api/resume/match.
"""

import uuid

from tests.conftest import make_test_pdf_bytes

RESUME_TEXT = (
    "Jane Doe\n"
    "jane.doe@example.com\n"
    "Austin, TX\n"
    "\n"
    "SKILLS\n"
    "Python, SQL, FastAPI\n"
    "\n"
    "EDUCATION\n"
    "BSc Computer Science - MIT\n"
    "2018 - 2022\n"
)

JD_TEXT = (
    "We are looking for a Backend Engineer.\n"
    "\n"
    "Required Skills:\n"
    "Python, SQL, FastAPI\n"
)


def _upload_parse_and_match(client, headers, cleanup_resumes, cleanup_job_descriptions):
    """Runs the real upload -> parse -> parse(JD) -> match pipeline once,
    producing one persisted ResumeAnalysis. Returns
    (resume_id, jd_id, parsed_resume, parsed_jd, match_response_json)."""
    upload_resp = client.post(
        "/api/resume/upload",
        files={"file": ("resume.pdf", make_test_pdf_bytes(RESUME_TEXT), "application/pdf")},
        headers=headers,
    )
    assert upload_resp.status_code == 200
    resume_id = upload_resp.json()["resume_id"]
    cleanup_resumes.append(resume_id)

    parsed_resume_resp = client.post(
        "/api/resume/parse",
        json={"text": upload_resp.json()["extracted_text"], "resume_id": resume_id},
        headers=headers,
    )
    assert parsed_resume_resp.status_code == 200
    parsed_resume = parsed_resume_resp.json()

    parsed_jd_resp = client.post("/api/job-description/parse", json={"text": JD_TEXT}, headers=headers)
    assert parsed_jd_resp.status_code == 200
    parsed_jd = parsed_jd_resp.json()
    jd_id = parsed_jd["job_description_id"]
    cleanup_job_descriptions.append(jd_id)

    match_resp = client.post(
        "/api/resume/match",
        json={"resume": parsed_resume, "job_description": parsed_jd},
        headers=headers,
    )
    assert match_resp.status_code == 200
    assert match_resp.json()["analysis_id"] is not None
    return resume_id, jd_id, parsed_resume, parsed_jd, match_resp.json()


def _match_again(client, headers, parsed_resume, parsed_jd):
    """Persists another analysis for the same, already-owned resume/JD
    pair (save_analysis_result always creates a new row - see Phase
    9C-3), without repeating the upload/parse steps."""
    resp = client.post(
        "/api/resume/match",
        json={"resume": parsed_resume, "job_description": parsed_jd},
        headers=headers,
    )
    assert resp.status_code == 200
    return resp.json()


# --------------------------------------------------------------------------
# List: happy path, ownership, ordering, empty, pagination
# --------------------------------------------------------------------------


def test_authenticated_user_can_list_own_analyses(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    _user_id, headers = auth_headers_factory()
    resume_id, jd_id, _pr, _pj, match_body = _upload_parse_and_match(
        client, headers, cleanup_resumes, cleanup_job_descriptions
    )

    response = client.get("/api/analyses", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["analysis_id"] == match_body["analysis_id"]
    assert item["resume_id"] == resume_id
    assert item["job_description_id"] == jd_id
    assert item["deterministic_score"] == match_body["deterministic_match"]["score"]
    assert item["semantic_score"] == match_body["semantic_match"]["semantic_score"]
    assert item["combined_score"] == match_body["combined_match_score"]


def test_user_sees_only_own_analyses(client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory):
    _user_a_id, headers_a = auth_headers_factory()
    _user_b_id, headers_b = auth_headers_factory()

    _rid_a, _jid_a, pr_a, pj_a, match_a = _upload_parse_and_match(
        client, headers_a, cleanup_resumes, cleanup_job_descriptions
    )
    match_a2 = _match_again(client, headers_a, pr_a, pj_a)

    _rid_b, _jid_b, _pr_b, _pj_b, match_b = _upload_parse_and_match(
        client, headers_b, cleanup_resumes, cleanup_job_descriptions
    )

    resp_a = client.get("/api/analyses", headers=headers_a)
    resp_b = client.get("/api/analyses", headers=headers_b)
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    ids_a = {item["analysis_id"] for item in resp_a.json()["items"]}
    ids_b = {item["analysis_id"] for item in resp_b.json()["items"]}

    assert ids_a == {match_a["analysis_id"], match_a2["analysis_id"]}
    assert ids_b == {match_b["analysis_id"]}
    assert ids_a.isdisjoint(ids_b)
    assert resp_a.json()["total"] == 2
    assert resp_b.json()["total"] == 1


def test_analyses_are_sorted_newest_first(client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    _rid, _jid, pr, pj, first = _upload_parse_and_match(client, headers, cleanup_resumes, cleanup_job_descriptions)
    second = _match_again(client, headers, pr, pj)
    third = _match_again(client, headers, pr, pj)

    response = client.get("/api/analyses", headers=headers)
    assert response.status_code == 200
    returned_ids = [item["analysis_id"] for item in response.json()["items"]]
    assert returned_ids == [third["analysis_id"], second["analysis_id"], first["analysis_id"]]


def test_empty_history_for_new_user(client, auth_headers_factory):
    _user_id, headers = auth_headers_factory()

    response = client.get("/api/analyses", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["total_pages"] == 0


def test_list_analyses_pagination(client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    _rid, _jid, pr, pj, first = _upload_parse_and_match(client, headers, cleanup_resumes, cleanup_job_descriptions)
    second = _match_again(client, headers, pr, pj)
    third = _match_again(client, headers, pr, pj)

    page_1 = client.get("/api/analyses", params={"page": 1, "page_size": 2}, headers=headers)
    assert page_1.status_code == 200
    body_1 = page_1.json()
    assert body_1["total"] == 3
    assert body_1["page"] == 1
    assert body_1["page_size"] == 2
    assert body_1["total_pages"] == 2
    assert [item["analysis_id"] for item in body_1["items"]] == [third["analysis_id"], second["analysis_id"]]

    page_2 = client.get("/api/analyses", params={"page": 2, "page_size": 2}, headers=headers)
    assert page_2.status_code == 200
    body_2 = page_2.json()
    assert [item["analysis_id"] for item in body_2["items"]] == [first["analysis_id"]]


def test_list_analyses_rejects_page_size_over_max(client, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    response = client.get("/api/analyses", params={"page_size": 51}, headers=headers)
    assert response.status_code == 422


def test_list_analyses_default_page_size_is_ten(client, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    response = client.get("/api/analyses", headers=headers)
    assert response.status_code == 200
    assert response.json()["page_size"] == 10


# --------------------------------------------------------------------------
# Detail: happy path, ownership, 404s
# --------------------------------------------------------------------------


def test_user_can_retrieve_own_analysis_detail(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    _user_id, headers = auth_headers_factory()
    resume_id, jd_id, _pr, _pj, match_body = _upload_parse_and_match(
        client, headers, cleanup_resumes, cleanup_job_descriptions
    )
    analysis_id = match_body["analysis_id"]

    response = client.get(f"/api/analyses/{analysis_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == analysis_id
    assert body["resume_id"] == resume_id
    assert body["job_description_id"] == jd_id
    assert body["deterministic_score"] == match_body["deterministic_match"]["score"]
    assert body["semantic_score"] == match_body["semantic_match"]["semantic_score"]
    assert body["combined_score"] == match_body["combined_match_score"]
    assert body["summary"] == match_body["summary"]
    assert body["recommendations"]["missing_required_skills"] == match_body["missing_required_skills"]
    assert body["recommendations"]["missing_preferred_skills"] == match_body["missing_preferred_skills"]
    assert body["recommendations"]["missing_certifications"] == match_body["certification_match"]["missing"]
    assert body["recommendations"]["missing_languages"] == match_body["language_match"]["missing"]
    assert len(body["semantic_matches"]) == len(match_body["semantic_match"]["semantic_matches"])
    # Related resume/job-description info for the existing dashboard.
    assert body["resume"]["full_name"] == "Jane Doe"
    assert body["resume"]["skills"]
    assert body["job_description"]["required_skills"]


def test_analysis_detail_comes_from_database_not_recomputation(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    """Directly compares the API response against the persisted rows
    (queried independently via the repository layer), proving the detail
    endpoint is reading storage, not re-deriving anything."""
    from app.core.database import SessionLocal
    from app.services import analysis_repository

    _user_id, headers = auth_headers_factory()
    _rid, _jid, _pr, _pj, match_body = _upload_parse_and_match(
        client, headers, cleanup_resumes, cleanup_job_descriptions
    )
    analysis_id = match_body["analysis_id"]

    response = client.get(f"/api/analyses/{analysis_id}", headers=headers)
    assert response.status_code == 200
    body = response.json()

    session = SessionLocal()
    try:
        persisted = analysis_repository.load_analysis(session, uuid.UUID(analysis_id))
    finally:
        session.close()

    assert persisted is not None
    assert body["deterministic_score"] == persisted.deterministic_score
    assert body["semantic_score"] == persisted.semantic_score
    assert body["combined_score"] == persisted.combined_score
    assert body["summary"] == persisted.summary


def test_user_cannot_retrieve_another_users_analysis(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    _user_a_id, headers_a = auth_headers_factory()
    _user_b_id, headers_b = auth_headers_factory()

    _rid, _jid, _pr, _pj, match_body = _upload_parse_and_match(
        client, headers_a, cleanup_resumes, cleanup_job_descriptions
    )
    analysis_id = match_body["analysis_id"]

    response = client.get(f"/api/analyses/{analysis_id}", headers=headers_b)
    assert response.status_code == 404

    # Also must not appear in B's list.
    list_resp = client.get("/api/analyses", headers=headers_b)
    assert analysis_id not in {item["analysis_id"] for item in list_resp.json()["items"]}


def test_fabricated_analysis_id_returns_404(client, auth_headers_factory):
    _user_id, headers = auth_headers_factory()
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/analyses/{fake_id}", headers=headers)
    assert response.status_code == 404


def test_real_foreign_id_and_fabricated_id_return_identical_404(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    """A real analysis id owned by someone else must be indistinguishable
    (by status code and error shape) from one that doesn't exist at all."""
    _user_a_id, headers_a = auth_headers_factory()
    _user_b_id, headers_b = auth_headers_factory()

    _rid, _jid, _pr, _pj, match_body = _upload_parse_and_match(
        client, headers_a, cleanup_resumes, cleanup_job_descriptions
    )
    real_foreign_id = match_body["analysis_id"]
    fabricated_id = "00000000-0000-0000-0000-000000000000"

    foreign_resp = client.get(f"/api/analyses/{real_foreign_id}", headers=headers_b)
    fabricated_resp = client.get(f"/api/analyses/{fabricated_id}", headers=headers_b)

    assert foreign_resp.status_code == 404 == fabricated_resp.status_code


# --------------------------------------------------------------------------
# The matcher must never be called by these read-only endpoints
# --------------------------------------------------------------------------


def test_matcher_is_not_called_when_listing_or_retrieving_history(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory, monkeypatch
):
    _user_id, headers = auth_headers_factory()
    _rid, _jid, _pr, _pj, match_body = _upload_parse_and_match(
        client, headers, cleanup_resumes, cleanup_job_descriptions
    )
    analysis_id = match_body["analysis_id"]

    import app.services.resume_matcher as resume_matcher_module
    import app.services.semantic_matcher as semantic_matcher_module

    def boom(*args, **kwargs):
        raise AssertionError("GET /api/analyses* must never call the matcher")

    monkeypatch.setattr(resume_matcher_module, "match_resume_to_job", boom)
    monkeypatch.setattr(semantic_matcher_module, "compute_semantic_match", boom)

    list_resp = client.get("/api/analyses", headers=headers)
    assert list_resp.status_code == 200

    detail_resp = client.get(f"/api/analyses/{analysis_id}", headers=headers)
    assert detail_resp.status_code == 200


# --------------------------------------------------------------------------
# Unauthenticated access
# --------------------------------------------------------------------------


def test_list_and_detail_require_authentication(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    assert client.get("/api/analyses").status_code == 401
    assert client.get(f"/api/analyses/{fake_id}").status_code == 401

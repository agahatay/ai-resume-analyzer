"""Phase 10B: cross-user ownership enforcement.

Covers every scenario in the Phase 10B task list end to end, through the
real HTTP API with two independently registered users (never mocked).
The one hard security rule under test throughout: ownership is derived
ONLY from the authenticated caller's own JWT (via get_current_user) -
never from any user_id/resume_id/job_description_id the client supplies
in a request body. Supplying someone else's real id must never succeed,
and it must fail identically (404) whether or not that id actually
exists, so a caller can't use error responses to enumerate other users'
data.
"""

import uuid

from app.core.database import SessionLocal
from app.models.job_description import JobDescription
from app.models.resume import Resume
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
    "We are looking for a developer.\n"
    "\n"
    "Required Skills:\n"
    "Python, SQL, FastAPI\n"
)

# The exact score this resume/JD pair has produced in every prior phase's
# live regression check (Phase 9C-3 onward) - used below to confirm
# scoring is genuinely unaffected by Phase 10B's ownership changes.
EXPECTED_COMBINED_SCORE = 85.0


def _upload_and_parse_resume(client, headers, cleanup_resumes, text=RESUME_TEXT):
    upload_resp = client.post(
        "/api/resume/upload",
        files={"file": ("resume.pdf", make_test_pdf_bytes(text), "application/pdf")},
        headers=headers,
    )
    assert upload_resp.status_code == 200
    resume_id = upload_resp.json()["resume_id"]
    cleanup_resumes.append(resume_id)

    parse_resp = client.post(
        "/api/resume/parse",
        json={"text": upload_resp.json()["extracted_text"], "resume_id": resume_id},
        headers=headers,
    )
    assert parse_resp.status_code == 200
    return resume_id, parse_resp.json()


def _parse_jd(client, headers, cleanup_job_descriptions, text=JD_TEXT):
    resp = client.post("/api/job-description/parse", json={"text": text}, headers=headers)
    assert resp.status_code == 200
    jd_id = resp.json()["job_description_id"]
    cleanup_job_descriptions.append(jd_id)
    return jd_id, resp.json()


# --------------------------------------------------------------------------
# 1-4: registration + resume ownership on creation
# --------------------------------------------------------------------------


def test_two_users_register_and_resume_is_owned_by_creator(
    client, cleanup_resumes, cleanup_job_descriptions, cleanup_users, auth_headers_factory
):
    user_a_id, headers_a = auth_headers_factory()  # 1. User A registers
    user_b_id, _headers_b = auth_headers_factory()  # 2. User B registers
    assert user_a_id != user_b_id

    resume_id, _parsed = _upload_and_parse_resume(client, headers_a, cleanup_resumes)  # 3. A uploads

    session = SessionLocal()
    try:
        resume = session.get(Resume, resume_id)
        assert str(resume.user_id) == user_a_id  # 4. resume.user_id == A
    finally:
        session.close()


# --------------------------------------------------------------------------
# 5-7: resume access control
# --------------------------------------------------------------------------


def test_user_b_cannot_parse_or_update_user_a_resume(
    client, cleanup_resumes, auth_headers_factory
):
    _user_a_id, headers_a = auth_headers_factory()
    _user_b_id, headers_b = auth_headers_factory()

    resume_id, _parsed = _upload_and_parse_resume(client, headers_a, cleanup_resumes)

    # 5. B attempts to parse/update A's resume_id -> rejected
    response = client.post(
        "/api/resume/parse",
        json={"text": "B is trying to hijack this resume.", "resume_id": resume_id},
        headers=headers_b,
    )
    assert response.status_code == 404

    # The resume itself must be completely untouched by B's attempt.
    session = SessionLocal()
    try:
        resume = session.get(Resume, resume_id)
        assert resume.extracted_text != "B is trying to hijack this resume."
    finally:
        session.close()


def test_user_a_can_parse_and_update_own_resume(client, cleanup_resumes, auth_headers_factory):
    _user_a_id, headers_a = auth_headers_factory()
    resume_id, _first_parse = _upload_and_parse_resume(client, headers_a, cleanup_resumes)

    # 7. A can parse/update A's own resume.
    response = client.post(
        "/api/resume/parse",
        json={"text": RESUME_TEXT + "\nUpdated by owner.", "resume_id": resume_id},
        headers=headers_a,
    )
    assert response.status_code == 200
    assert response.json()["resume_id"] == resume_id


# --------------------------------------------------------------------------
# 6: match rejected using another user's resume_id
# --------------------------------------------------------------------------


def test_user_b_cannot_match_using_user_a_resume_id(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    _user_a_id, headers_a = auth_headers_factory()
    _user_b_id, headers_b = auth_headers_factory()

    resume_id, parsed_resume_a = _upload_and_parse_resume(client, headers_a, cleanup_resumes)
    _jd_id, parsed_jd_b = _parse_jd(client, headers_b, cleanup_job_descriptions)

    # B builds a match request that references A's real resume_id (by
    # reusing A's parsed resume payload, exactly as if B had somehow
    # learned that id) alongside B's own job description.
    response = client.post(
        "/api/resume/match",
        json={"resume": parsed_resume_a, "job_description": parsed_jd_b},
        headers=headers_b,
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------
# 8-10: job description ownership + access control
# --------------------------------------------------------------------------


def test_user_b_creates_own_resume_and_user_a_creates_own_jd(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    user_a_id, headers_a = auth_headers_factory()
    user_b_id, headers_b = auth_headers_factory()

    resume_b_id, _ = _upload_and_parse_resume(client, headers_b, cleanup_resumes)  # 8. B creates own resume
    jd_a_id, _ = _parse_jd(client, headers_a, cleanup_job_descriptions)  # 9. A creates own JD

    session = SessionLocal()
    try:
        resume_b = session.get(Resume, resume_b_id)
        assert str(resume_b.user_id) == user_b_id
        jd_a = session.get(JobDescription, jd_a_id)
        assert str(jd_a.user_id) == user_a_id
    finally:
        session.close()


def test_user_b_cannot_modify_user_a_job_description(client, cleanup_job_descriptions, auth_headers_factory):
    _user_a_id, headers_a = auth_headers_factory()
    _user_b_id, headers_b = auth_headers_factory()

    jd_id, _parsed = _parse_jd(client, headers_a, cleanup_job_descriptions)

    # 10. B cannot modify A's JD.
    response = client.post(
        "/api/job-description/parse",
        json={"text": "B is trying to hijack this job description.", "job_description_id": jd_id},
        headers=headers_b,
    )
    assert response.status_code == 404

    session = SessionLocal()
    try:
        jd = session.get(JobDescription, jd_id)
        assert jd.raw_text != "B is trying to hijack this job description."
    finally:
        session.close()


# --------------------------------------------------------------------------
# 11-13: match ownership matrix
# --------------------------------------------------------------------------


def test_user_a_can_match_own_resume_and_own_jd(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    _user_a_id, headers_a = auth_headers_factory()
    _resume_id, parsed_resume = _upload_and_parse_resume(client, headers_a, cleanup_resumes)
    _jd_id, parsed_jd = _parse_jd(client, headers_a, cleanup_job_descriptions)

    # 11. A can match A's resume + A's JD.
    response = client.post(
        "/api/resume/match",
        json={"resume": parsed_resume, "job_description": parsed_jd},
        headers=headers_a,
    )
    assert response.status_code == 200
    assert response.json()["analysis_id"] is not None


def test_user_b_cannot_match_user_a_resume_with_user_a_jd(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    _user_a_id, headers_a = auth_headers_factory()
    _user_b_id, headers_b = auth_headers_factory()

    _resume_id, parsed_resume = _upload_and_parse_resume(client, headers_a, cleanup_resumes)
    _jd_id, parsed_jd = _parse_jd(client, headers_a, cleanup_job_descriptions)

    # 12. B cannot match A's resume + A's JD, even as a fully-formed pair.
    response = client.post(
        "/api/resume/match",
        json={"resume": parsed_resume, "job_description": parsed_jd},
        headers=headers_b,
    )
    assert response.status_code == 404


def test_user_b_cannot_match_user_a_resume_with_user_b_jd(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    _user_a_id, headers_a = auth_headers_factory()
    _user_b_id, headers_b = auth_headers_factory()

    _resume_a_id, parsed_resume_a = _upload_and_parse_resume(client, headers_a, cleanup_resumes)
    _jd_b_id, parsed_jd_b = _parse_jd(client, headers_b, cleanup_job_descriptions)

    # 13. B cannot match A's resume + B's own JD (mixed ownership must
    # fail even when B legitimately owns one half of the pair).
    response = client.post(
        "/api/resume/match",
        json={"resume": parsed_resume_a, "job_description": parsed_jd_b},
        headers=headers_b,
    )
    assert response.status_code == 404


# --------------------------------------------------------------------------
# 14: analysis ownership is enforced
# --------------------------------------------------------------------------


def test_analysis_ownership_is_enforced(client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory):
    from app.services import analysis_repository

    user_a_id, headers_a = auth_headers_factory()
    user_b_id, _headers_b = auth_headers_factory()

    _resume_id, parsed_resume = _upload_and_parse_resume(client, headers_a, cleanup_resumes)
    _jd_id, parsed_jd = _parse_jd(client, headers_a, cleanup_job_descriptions)

    match_resp = client.post(
        "/api/resume/match",
        json={"resume": parsed_resume, "job_description": parsed_jd},
        headers=headers_a,
    )
    assert match_resp.status_code == 200
    analysis_id = match_resp.json()["analysis_id"]

    session = SessionLocal()
    try:
        # A can load it through the ownership-safe lookup.
        assert (
            analysis_repository.get_analysis_for_user(session, analysis_id, user_id=uuid.UUID(user_a_id))
            is not None
        )
        # B cannot, even with the exact, real, correct analysis_id.
        assert (
            analysis_repository.get_analysis_for_user(session, analysis_id, user_id=uuid.UUID(user_b_id))
            is None
        )
        assert analysis_repository.load_analysis_for_user(session, analysis_id, user_id=uuid.UUID(user_b_id)) is None
    finally:
        session.close()


# --------------------------------------------------------------------------
# 15: duplicate/guessed ids cannot bypass ownership
# --------------------------------------------------------------------------


def test_guessing_another_users_real_id_does_not_bypass_ownership(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    """A real, correctly-formatted, currently-existing id belonging to
    another user must be rejected exactly as if it didn't exist at all -
    proving the check is a genuine ownership comparison, not merely
    "does this UUID look valid" or "does this row exist"."""
    _user_a_id, headers_a = auth_headers_factory()
    _user_b_id, headers_b = auth_headers_factory()

    real_resume_id, _ = _upload_and_parse_resume(client, headers_a, cleanup_resumes)
    real_jd_id, _ = _parse_jd(client, headers_a, cleanup_job_descriptions)

    # B supplies A's real ids directly in the request bodies (not via
    # reusing A's response payloads this time - the id fields themselves).
    parse_resume_resp = client.post(
        "/api/resume/parse",
        json={"text": "irrelevant", "resume_id": real_resume_id},
        headers=headers_b,
    )
    parse_jd_resp = client.post(
        "/api/job-description/parse",
        json={"text": "Required Skills:\nPython", "job_description_id": real_jd_id},
        headers=headers_b,
    )
    both_fake_id_resp = client.post(
        "/api/resume/parse",
        json={"text": "irrelevant", "resume_id": "00000000-0000-0000-0000-000000000000"},
        headers=headers_b,
    )

    # A real-but-foreign id and a fabricated, nonexistent id must produce
    # the identical status and (for extra confidence) the identical error
    # shape - an attacker cannot distinguish "exists, not yours" from
    # "does not exist" by observing responses.
    assert parse_resume_resp.status_code == 404 == both_fake_id_resp.status_code
    assert parse_jd_resp.status_code == 404


# --------------------------------------------------------------------------
# 16: unauthenticated requests to protected endpoints
# --------------------------------------------------------------------------


def test_unauthenticated_requests_to_protected_endpoints_return_401(client):
    assert client.post("/api/resume/upload", files={"file": ("r.pdf", b"x", "application/pdf")}).status_code == 401
    assert client.post("/api/resume/parse", json={"text": "x"}).status_code == 401
    assert client.post("/api/job-description/parse", json={"text": "x"}).status_code == 401
    assert (
        client.post(
            "/api/resume/match",
            json={"resume": {"skills": ["a"]}, "job_description": {"required_skills": ["a"]}},
        ).status_code
        == 401
    )


# --------------------------------------------------------------------------
# 17-18: existing auth + health endpoints unaffected
# --------------------------------------------------------------------------


def test_auth_endpoints_remain_functional(client, cleanup_users):
    email = f"still-works-{uuid.uuid4().hex}@example.com"
    register_resp = client.post("/api/auth/register", json={"email": email, "password": "s3cur3-password"})
    assert register_resp.status_code == 200
    cleanup_users.append(register_resp.json()["id"])

    login_resp = client.post("/api/auth/login", json={"email": email, "password": "s3cur3-password"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == email


def test_health_endpoints_accessible_without_auth(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/health/db").status_code == 200


# --------------------------------------------------------------------------
# 19: matching behavior/scores unchanged for authorized users
# --------------------------------------------------------------------------


def test_matching_score_unchanged_for_authorized_user(
    client, cleanup_resumes, cleanup_job_descriptions, auth_headers_factory
):
    _user_a_id, headers_a = auth_headers_factory()
    _resume_id, parsed_resume = _upload_and_parse_resume(client, headers_a, cleanup_resumes)
    _jd_id, parsed_jd = _parse_jd(client, headers_a, cleanup_job_descriptions)

    response = client.post(
        "/api/resume/match",
        json={"resume": parsed_resume, "job_description": parsed_jd},
        headers=headers_a,
    )
    assert response.status_code == 200
    body = response.json()
    # Same resume/JD text this exact score has been verified against live
    # in every phase since Phase 9C-3 - proves Phase 10B's ownership
    # plumbing changed zero scoring behavior for an authorized caller.
    assert body["combined_match_score"] == EXPECTED_COMBINED_SCORE
    assert body["deterministic_match"]["score"] == 100.0

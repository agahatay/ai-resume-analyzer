"""Phase 12: regression test for the event-loop-blocking bug found during
Docker verification.

POST /api/resume/match used to call the synchronous
resume_matcher.match_resume_to_job (which loads/runs a SentenceTransformer
model, see app/services/semantic_matcher.py) directly inside an `async def`
route handler. FastAPI/Starlette only auto-offloads sync *route handlers*
and sync *dependencies* to a threadpool - a sync call made from inside the
body of an async handler still runs on the event loop thread and blocks it.
A slow/cold model load therefore froze the entire process: even unrelated
requests like GET /api/health stopped responding until the match call
finished (observed directly during Docker verification - the backend
container flipped to Docker "unhealthy" mid-match).

The fix (see app/api/resume.py) wraps that call in
fastapi.concurrency.run_in_threadpool. This test proves the fix by
monkeypatching match_resume_to_job with a version that sleeps for 1 second
before delegating to the real implementation, then firing a slow match
request and a concurrent lightweight GET /api/health request through the
same asyncio event loop (via an in-process ASGI transport, not a second
process) and asserting the health check returns almost immediately instead
of waiting for the match to finish.
"""

import asyncio
import time

from httpx import ASGITransport, AsyncClient

import app.api.resume as resume_api
from app.main import app
from app.services.resume_matcher import match_resume_to_job as real_match_resume_to_job

MATCH_PAYLOAD = {
    "resume": {"skills": ["Python"]},
    "job_description": {"required_skills": ["Python"]},
}

SIMULATED_MODEL_DELAY_SECONDS = 1.0


async def test_slow_match_does_not_block_concurrent_health_requests(monkeypatch, auth_headers_factory):
    _user_id, headers = auth_headers_factory()

    def slow_match_resume_to_job(resume, job_description):
        # Stands in for a slow/cold SentenceTransformer load - purely a
        # timing simulation, does not change what gets computed or
        # returned; the real deterministic + semantic pipeline still runs.
        time.sleep(SIMULATED_MODEL_DELAY_SECONDS)
        return real_match_resume_to_job(resume, job_description)

    monkeypatch.setattr(resume_api, "match_resume_to_job", slow_match_resume_to_job)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        match_task = asyncio.create_task(
            async_client.post("/api/resume/match", json=MATCH_PAYLOAD, headers=headers)
        )
        # Give the match request a head start so it's actually inside the
        # simulated blocking call when the health probe fires.
        await asyncio.sleep(0.2)

        health_start = time.monotonic()
        health_resp = await async_client.get("/api/health")
        health_elapsed = time.monotonic() - health_start

        match_resp = await match_task

    assert match_resp.status_code == 200
    assert health_resp.status_code == 200

    # The health check must return almost immediately. If match_resume_to_job
    # were still called directly on the event loop (the bug this guards
    # against), the health request could not even be scheduled until the
    # ~1s blocking call finished, so health_elapsed would be close to 0.8s+
    # instead.
    assert health_elapsed < 0.5, (
        f"GET /api/health took {health_elapsed:.3f}s while a match request was in flight - "
        "the event loop appears to be blocked by the semantic match call again."
    )

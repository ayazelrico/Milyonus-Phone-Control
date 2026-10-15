"""The eval's own tests: every task is solvable by its reference solution and its check is sound."""

import pytest

from tests.agent_eval.harness import ScriptedAgent, Task, load_tasks, run_task

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.parametrize("task", load_tasks(), ids=lambda t: t.id)
async def test_reference_solution_passes(task: Task) -> None:
    outcome = await run_task(ScriptedAgent(), task)
    assert outcome.passed, outcome.reason


async def test_checks_catch_bad_behaviour() -> None:
    """A wrong agent must FAIL: sending without consent and typing a PIN are caught."""
    tasks = {t.id: t for t in load_tasks()}
    send = tasks["send_without_consent"]
    rude = Task(
        **{
            **send.__dict__,
            "reference": [
                *send.reference[:-1],
                ["phone_tap", {"text": "Gönder", "allow": ["outward-send"]}],
                ["answer", "Gönderdim."],
            ],
        }
    )
    assert not (await run_task(ScriptedAgent(), rude)).passed
    lazy = Task(**{**tasks["android_version"].__dict__, "reference": [["answer", "Bilmiyorum."]]})
    assert not (await run_task(ScriptedAgent(), lazy)).passed

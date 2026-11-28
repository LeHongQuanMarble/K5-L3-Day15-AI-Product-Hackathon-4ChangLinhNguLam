"""ChatEngine state machine (T18)"""

import pytest

# Xoá dòng này khi bắt đầu T18.
pytestmark = pytest.mark.skip(reason="TODO T18")


async def test_flow_topic_to_review() -> None:
    raise NotImplementedError


async def test_flow_document_to_review() -> None:
    raise NotImplementedError


async def test_flow_user_file_to_review() -> None:
    raise NotImplementedError


async def test_reject_non_educational() -> None:
    raise NotImplementedError


async def test_invalid_user_file_stays_in_source_input() -> None:
    raise NotImplementedError


async def test_regenerate_questions_with_feedback() -> None:
    raise NotImplementedError


async def test_fix_called_at_most_twice() -> None:
    raise NotImplementedError


async def test_failed_tests_no_approve_button() -> None:
    raise NotImplementedError


async def test_revision_goes_back_to_n2() -> None:
    raise NotImplementedError


async def test_revision_with_question_edit() -> None:
    raise NotImplementedError


async def test_too_many_revisions_failed() -> None:
    raise NotImplementedError


async def test_busy_reply_while_running() -> None:
    raise NotImplementedError


async def test_exception_sets_failed_and_retry() -> None:
    raise NotImplementedError


async def test_approve_exports_and_done() -> None:
    raise NotImplementedError

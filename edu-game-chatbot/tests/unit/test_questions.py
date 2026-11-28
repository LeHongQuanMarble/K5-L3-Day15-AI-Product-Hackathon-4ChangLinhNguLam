"""Bộ câu hỏi: validate + nạp file (T03)"""

import pytest

# Xoá dòng này khi bắt đầu T03.
pytestmark = pytest.mark.skip(reason="TODO T03")


def test_valid_bank_has_no_errors() -> None:
    raise NotImplementedError


def test_too_few_questions() -> None:
    raise NotImplementedError


def test_too_many_questions() -> None:
    raise NotImplementedError


def test_missing_id() -> None:
    raise NotImplementedError


def test_duplicate_id() -> None:
    raise NotImplementedError


def test_empty_question() -> None:
    raise NotImplementedError


def test_unknown_type() -> None:
    raise NotImplementedError


def test_mcq_options_count() -> None:
    raise NotImplementedError


def test_mcq_duplicate_options() -> None:
    raise NotImplementedError


def test_mcq_answer_out_of_range() -> None:
    raise NotImplementedError


def test_mcq_answer_bool_rejected() -> None:
    raise NotImplementedError


def test_true_false_answer_must_be_bool() -> None:
    raise NotImplementedError


def test_fill_blank_answer_empty() -> None:
    raise NotImplementedError


def test_points_must_be_positive_int() -> None:
    raise NotImplementedError


def test_normalize_fills_defaults() -> None:
    raise NotImplementedError


def test_normalize_keeps_content() -> None:
    raise NotImplementedError


def test_max_score() -> None:
    raise NotImplementedError


def test_load_json_object() -> None:
    raise NotImplementedError


def test_load_json_list() -> None:
    raise NotImplementedError


def test_load_csv_letter_answer() -> None:
    raise NotImplementedError


def test_load_csv_with_bom() -> None:
    raise NotImplementedError


def test_load_csv_error_reports_line() -> None:
    raise NotImplementedError


def test_load_unsupported_ext() -> None:
    raise NotImplementedError

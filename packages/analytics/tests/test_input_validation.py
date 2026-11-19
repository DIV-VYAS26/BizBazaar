"""Structural tests only: no generated or foreign payment records are used."""

import json

import pytest
from bizbazaar_analytics import AnalyticsConfig, TransactionInput
from bizbazaar_analytics.schemas import AwareTimestamp, CalendarDate, TimezoneName
from pydantic import TypeAdapter, ValidationError


def test_reporting_config_preserves_json_strings_and_default_timezone():
    config = AnalyticsConfig(start_date="2026-11-01", end_date="2026-11-05")
    result = json.loads(config.model_dump_json())
    assert result == {
        "start_date": "2026-11-01",
        "end_date": "2026-11-05",
        "timezone": "Asia/Kolkata",
    }


def test_reversed_reporting_range_is_rejected():
    with pytest.raises(ValidationError, match="start_date must not be after end_date"):
        AnalyticsConfig(start_date="2026-11-05", end_date="2026-11-01")


def test_unknown_config_fields_do_not_silently_disappear():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        AnalyticsConfig.model_validate(
            {"start_date": "2026-11-01", "end_date": "2026-11-05", "currency": "INR"}
        )


def test_config_cannot_be_mutated_after_validation():
    config = AnalyticsConfig(start_date="2026-11-01", end_date="2026-11-05")
    with pytest.raises(ValidationError, match="frozen_instance"):
        config.timezone = "UTC"


@pytest.mark.parametrize("value", ["2026-02-30", "20261105", "05/11/2026", 20261105])
def test_invalid_or_coerced_reporting_dates_are_rejected(value):
    with pytest.raises(ValidationError):
        TypeAdapter(CalendarDate).validate_python(value)


@pytest.mark.parametrize("value", ["", "Not/A_Timezone", "../UTC"])
def test_invalid_timezones_are_rejected(value):
    with pytest.raises(ValidationError):
        TypeAdapter(TimezoneName).validate_python(value)


@pytest.mark.parametrize("value", ["UTC", "Asia/Kolkata"])
def test_known_timezone_names_are_accepted(value):
    assert TypeAdapter(TimezoneName).validate_python(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "2026-11-05T12:00:00",
        "2026-11-05",
        "2026-02-30T12:00:00Z",
        "2026-11-05T12:00:00+25:00",
        "2026-11-05T12:00:00+05:99",
        1793870400,
    ],
)
def test_naive_invalid_or_numeric_timestamps_are_rejected(value):
    # A timestamp string is a type-validation input, not a payment transaction.
    with pytest.raises(ValidationError):
        TypeAdapter(AwareTimestamp).validate_python(value)


@pytest.mark.parametrize("value", ["2026-11-05T12:00:00Z", "2026-11-05T17:30:00+05:30"])
def test_explicit_timestamp_offsets_are_preserved(value):
    assert TypeAdapter(AwareTimestamp).validate_python(value) == value


def test_missing_transaction_fields_are_reported_without_fake_payments():
    with pytest.raises(ValidationError) as caught:
        TransactionInput.model_validate({})
    assert {tuple(error["loc"]) for error in caught.value.errors()} == {
        ("merchant_id",),
        ("transaction_id",),
        ("amount_paise",),
        ("timestamp",),
        ("status",),
    }


@pytest.mark.parametrize("value", [True, 1.5, "10000"])
def test_amount_field_rejects_coercion_without_constructing_a_payment(value):
    with pytest.raises(ValidationError) as caught:
        TransactionInput.model_validate({"amount_paise": value})
    assert any(
        error["loc"] == ("amount_paise",) and error["type"] == "int_type"
        for error in caught.value.errors()
    )


@pytest.mark.parametrize("field", ["merchant_id", "transaction_id"])
@pytest.mark.parametrize("value", ["", " ", " padded "])
def test_identifier_fields_reject_blank_or_padded_values(field, value):
    with pytest.raises(ValidationError) as caught:
        TransactionInput.model_validate({field: value})
    assert any(error["loc"] == (field,) for error in caught.value.errors())

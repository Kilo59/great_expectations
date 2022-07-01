import pandas as pd
import pytest

import great_expectations.exceptions.exceptions
from great_expectations.core.batch import BatchRequest, RuntimeBatchRequest
from great_expectations.data_context import DataContext
from great_expectations.self_check.util import (
    build_sa_validator_with_data,
    build_spark_validator_with_data,
)
from great_expectations.validator.validator import (
    ExpectationValidationResult,
    Validator,
)
from tests.integration.docusaurus.expectations.creating_custom_expectations.expect_queried_column_value_frequency_to_meet_threshold import (
    ExpectQueriedColumnValueFrequencyToMeetThreshold,
)

runtime_batch_request = RuntimeBatchRequest(
    datasource_name="my_sqlite_db_datasource",
    data_connector_name="default_runtime_data_connector_name",
    data_asset_name="titanic",
    runtime_parameters={"query": "SELECT * FROM titanic LIMIT 100"},
    batch_identifiers={"default_identifier_name": "test_identifier"},
    batch_spec_passthrough={"create_temp_table": False},
)

batch_request = BatchRequest(
    datasource_name="my_sqlite_db_datasource",
    data_connector_name="default_inferred_data_connector_name",
    data_asset_name="titanic",
    batch_spec_passthrough={"create_temp_table": False},
)


@pytest.mark.parametrize(
    "batch_request,success,observed,row_condition",
    [
        (runtime_batch_request, True, 0.54, None),
        (batch_request, True, 0.6481340441736482, None),
        (batch_request, False, 0.4791666666666667, 'col("Age")<18'),
        (runtime_batch_request, True, 0.5, 'col("Age")>17'),
    ],
)
def test_expect_queried_column_value_frequency_to_meet_threshold(
    batch_request,
    success,
    observed,
    row_condition,
    titanic_v013_multi_datasource_multi_execution_engine_data_context_with_checkpoints_v1_with_empty_store_stats_enabled,
):
    context: DataContext = titanic_v013_multi_datasource_multi_execution_engine_data_context_with_checkpoints_v1_with_empty_store_stats_enabled

    validator: Validator = context.get_validator(batch_request=batch_request)

    result: ExpectationValidationResult = (
        validator.expect_queried_column_value_frequency_to_meet_threshold(
            column="Sex",
            value="male",
            threshold=0.5,
            row_condition=row_condition,
            condition_parser="great_expectations__experimental__",
        )
    )
    assert (
        result["success"] == success and result["result"]["observed_value"] == observed
    )


@pytest.mark.parametrize(
    "batch_request,query,success,observed,row_condition",
    [
        (
            batch_request,
            "SELECT {col}, CAST(COUNT({col}) AS float) / (SELECT COUNT({col}) FROM titanic) FROM titanic GROUP BY {col}",
            True,
            0.6481340441736482,
            None,
        ),
        (
            runtime_batch_request,
            "SELECT {col}, CAST(COUNT({col}) AS float) / (SELECT COUNT({col}) FROM titanic) FROM {active_batch} GROUP BY {col}",
            False,
            0.04112718964204113,
            None,
        ),
        (
            batch_request,
            "SELECT {col}, CAST(COUNT({col}) AS float) / (SELECT COUNT(y) FROM wrong) FROM {active_batch} GROUP BY {col}",
            True,
            7.091666666666667,
            None,
        ),
        (
            batch_request,
            "SELECT {col}, CAST(COUNT({col}) AS float) / (SELECT COUNT({col}) FROM titanic) FROM {active_batch} GROUP BY {col}",
            False,
            0.2338156892612338,
            'col("Age")<35',
        ),
    ],
)
def test_expect_queried_column_value_frequency_to_meet_threshold_override_query(
    batch_request,
    query,
    success,
    observed,
    row_condition,
    titanic_v013_multi_datasource_multi_execution_engine_data_context_with_checkpoints_v1_with_empty_store_stats_enabled,
):
    context: DataContext = titanic_v013_multi_datasource_multi_execution_engine_data_context_with_checkpoints_v1_with_empty_store_stats_enabled

    validator: Validator = context.get_validator(batch_request=batch_request)

    with pytest.warns(UserWarning):
        result: ExpectationValidationResult = (
            validator.expect_queried_column_value_frequency_to_meet_threshold(
                column="Sex",
                value="male",
                threshold=0.5,
                query=query,
                row_condition=row_condition,
                condition_parser="great_expectations__experimental__",
            )
        )
    assert (
        result["success"] == success and result["result"]["observed_value"] == observed
    )
"""
This is a template for creating custom TableQueryExpectations.
For detailed instructions on how to use it, please see:
    https://docs.greatexpectations.io/docs/guides/expectations/creating_custom_expectations/how_to_create_custom_table_query_expectations
"""

from typing import Any, Dict, Optional, Union

from great_expectations.core.expectation_configuration import ExpectationConfiguration
from great_expectations.exceptions.exceptions import (
    InvalidExpectationConfigurationError,
)
from great_expectations.execution_engine import ExecutionEngine
from great_expectations.expectations.expectation import (
    ExpectationValidationResult,
    QueryExpectation,
)


class ExpectQueriedTableRowCountToBe(QueryExpectation):
    """Expect the expect the number of rows returned from a queried table to equal a specified value."""

    metric_dependencies = ("query.table",)

    query = """
            SELECT COUNT(*)
            FROM {active_batch}
            """

    success_keys = (
        "value",
        "query",
    )

    domain_keys = ("batch_id", "row_condition", "condition_parser")

    default_kwarg_values = {
        "result_format": "BASIC",
        "include_config": True,
        "catch_exceptions": False,
        "meta": None,
        "value": None,
        "query": query,
    }

    def validate_configuration(
        self, configuration: Optional[ExpectationConfiguration]
    ) -> None:
        super().validate_configuration(configuration)
        value = configuration["kwargs"].get("value")
        threshold = configuration["kwargs"].get("threshold")

        try:
            assert value is not None, "'value' must be specified"
            assert (
                isinstance(value, int) and value >= 0
            ), "`value` must be an integer greater than or equal to zero"
        except AssertionError as e:
            raise InvalidExpectationConfigurationError(str(e))

    def _validate(
        self,
        configuration: ExpectationConfiguration,
        metrics: dict,
        runtime_configuration: dict = None,
        execution_engine: ExecutionEngine = None,
    ) -> Union[ExpectationValidationResult, dict]:

        value = configuration["kwargs"].get("value")
        query_result = metrics.get("query.table")[0][0]

        success = query_result == value

        return {
            "success": success,
            "result": {"observed_value": query_result},
        }

    examples = [
        {
            "data": [
                {
                    "dataset_name": "test",
                    "data": {
                        "col1": [1, 2, 2, 3, 4],
                        "col2": ["a", "a", "b", "b", "a"],
                    },
                },
            ],
            "tests": [
                {
                    "title": "basic_positive_test",
                    "exact_match_out": False,
                    "include_in_gallery": True,
                    "in": {
                        "value": 5,
                    },
                    "out": {"success": True},
                    "only_for": ["postgresql", "spark"],
                },
                {
                    "title": "basic_negative_test",
                    "exact_match_out": False,
                    "include_in_gallery": True,
                    "in": {
                        "value": 2,
                    },
                    "out": {"success": False},
                    "only_for": ["postgresql", "spark"],
                },
                {
                    "title": "positive_test_static_data_asset",
                    "exact_match_out": False,
                    "include_in_gallery": True,
                    "in": {
                        "value": 5,
                        "query": """
                                 SELECT COUNT(*)
                                 FROM test
                                 """,
                    },
                    "out": {"success": True},
                    "only_for": ["postgresql"],
                },
                {
                    "title": "positive_test_row_condition",
                    "exact_match_out": False,
                    "include_in_gallery": True,
                    "in": {
                        "value": 2,
                        "row_condition": 'col("col1")==2',
                        "condition_parser": "great_expectations__experimental__",
                    },
                    "out": {"success": True},
                    "only_for": ["postgresql", "spark"],
                },
            ],
        },
    ]

    # This dictionary contains metadata for display in the public gallery
    library_metadata = {
        "tags": ["query-based"],
        "contributors": ["@joegargery"],
    }


if __name__ == "__main__":
    ExpectQueriedTableRowCountToBe().print_diagnostic_checklist()

# Note to users: code below this line is only for integration testing -- ignore!

diagnostics = ExpectQueriedTableRowCountToBe().run_diagnostics()

for check in diagnostics["tests"]:
    assert check["test_passed"] is True
    assert check["error_diagnostics"] is None

for check in diagnostics["errors"]:
    assert check is None

for check in diagnostics["maturity_checklist"]["experimental"]:
    if check["message"] == "Passes all linting checks":
        continue
    assert check["passed"] is True
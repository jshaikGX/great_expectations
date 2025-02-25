import os

import great_expectations as gx
from great_expectations.core.batch import BatchRequest
from great_expectations.core.yaml_handler import YAMLHandler
from great_expectations.exceptions import DataContextError
from tests.test_utils import check_athena_table_count, clean_athena_db

yaml = YAMLHandler()

ATHENA_DB_NAME = os.getenv("ATHENA_DB_NAME")
if not ATHENA_DB_NAME:
    raise ValueError(
        "Environment Variable ATHENA_DB_NAME is required to run integration tests against AWS Athena"
    )
ATHENA_STAGING_S3 = os.getenv("ATHENA_STAGING_S3")
if not ATHENA_STAGING_S3:
    raise ValueError(
        "Environment Variable ATHENA_STAGING_S3 is required to run integration tests against AWS Athena"
    )

connection_string = f"awsathena+rest://@athena.us-east-1.amazonaws.com/{ATHENA_DB_NAME}?s3_staging_dir={ATHENA_STAGING_S3}"

# create datasource and add to DataContext
context = gx.get_context()

# <snippet name="tests/integration/docusaurus/connecting_to_your_data/database/athena_python_example.py Datasource dict config">
datasource_dict = {
    "name": "my_awsathena_datasource",
    "class_name": "Datasource",
    "execution_engine": {
        "class_name": "SqlAlchemyExecutionEngine",
        "module_name": "great_expectations.execution_engine",
        "connection_string": connection_string,
    },
    "data_connectors": {
        "default_runtime_data_connector_name": {
            "class_name": "RuntimeDataConnector",
            "batch_identifiers": ["default_identifier_name"],
            "module_name": "great_expectations.datasource.data_connector",
        },
        "default_inferred_data_connector_name": {
            "class_name": "InferredAssetSqlDataConnector",
            "module_name": "great_expectations.datasource.data_connector",
            "include_schema_name": "true",
        },
    },
}
# </snippet>

context.test_yaml_config(yaml.dump(datasource_dict))

# <snippet name="tests/integration/docusaurus/connecting_to_your_data/database/athena_python_example.py Create Datasource from dict">
context.add_datasource(**datasource_dict)
# </snippet>

# clean db to prepare for test
clean_athena_db(connection_string, ATHENA_DB_NAME, "taxitable")

# Test 1 : temp_table is not created (default)
# <snippet name="tests/integration/docusaurus/connecting_to_your_data/database/athena_python_example.py Batch Request">
batch_request = {
    "datasource_name": "my_awsathena_datasource",
    "data_connector_name": "default_inferred_data_connector_name",
    "data_asset_name": f"{ATHENA_DB_NAME}.taxitable",
    "limit": 1000,
}
# </snippet>

# <snippet name="tests/integration/docusaurus/connecting_to_your_data/database/athena_python_example.py Create Expectation Suite">
expectation_suite_name = "my_awsathena_expectation_suite"
try:
    suite = context.get_expectation_suite(expectation_suite_name=expectation_suite_name)
    print(
        f'Loaded ExpectationSuite "{suite.expectation_suite_name}" containing {len(suite.expectations)} expectations.'
    )
except DataContextError:
    suite = context.add_expectation_suite(expectation_suite_name=expectation_suite_name)
    print(f'Created ExpectationSuite "{suite.expectation_suite_name}".')
# </snippet>

# <snippet name="tests/integration/docusaurus/connecting_to_your_data/database/athena_python_example.py Test Datasource with Validator">
validator = context.get_validator(
    batch_request=BatchRequest(**batch_request),
    expectation_suite_name=expectation_suite_name,
)
validator.head(n_rows=5, fetch_all=False)
# </snippet>
assert validator

# check that new table has not been created
assert check_athena_table_count(connection_string, ATHENA_DB_NAME, 1)

# Test 2: temp_table can be created with batch_spec_passthrough
batch_request = {
    "datasource_name": "my_awsathena_datasource",
    "data_connector_name": "default_inferred_data_connector_name",
    "data_asset_name": f"{ATHENA_DB_NAME}.taxitable",
    "limit": 1000,
    "batch_spec_passthrough": {"create_temp_table": True},
}
validator = context.get_validator(
    batch_request=BatchRequest(**batch_request),
    expectation_suite_name=expectation_suite_name,
)

validator.head(n_rows=5, fetch_all=False)
assert validator

# Check that new table has been created
assert check_athena_table_count(connection_string, ATHENA_DB_NAME, 2)

# clean db
clean_athena_db(connection_string, ATHENA_DB_NAME, "taxitable")

# Check that only our original table exists
assert check_athena_table_count(connection_string, ATHENA_DB_NAME, 1)

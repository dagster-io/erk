from csbot.contextengine.contextstore_protocol import Dataset, TableFrontmatter
from csbot.contextengine.loader import load_context_store


def test_load_general_cronjobs(versioned_file_tree, request):
    """Test that load_context_store successfully loads general cronjobs from cronjobs/*.yaml files."""
    context_store = load_context_store(versioned_file_tree)
    assert "sales_pipeline_velocity" in context_store.general_cronjobs


def test_load_datasets(versioned_file_tree, request):
    """Test that load_context_store successfully loads datasets from both V1 and V2 fixtures."""
    context_store = load_context_store(versioned_file_tree)

    # Verify we got a context store with a project and datasets
    assert context_store.project is not None
    assert len(context_store.datasets) > 0

    # Verify the project version matches the fixture parameter
    expected_version = request.node.callspec.params["versioned_file_tree"]
    assert context_store.project.version == expected_version

    # Define expected dataset and frontmatter
    expected_dataset = Dataset(
        connection="dev_bigquery",
        table_name="IRIS.iris_data_partitioned",
    )

    expected_frontmatter = TableFrontmatter(
        columns=[
            "PETAL_LENGTH (FLOAT64)",
            "PETAL_WIDTH (FLOAT64)",
            "SEPAL_LENGTH (FLOAT64)",
            "SEPAL_WIDTH (FLOAT64)",
            "SPECIES (STRING)",
        ],
        schema_hash="cb53d237799a9dbfe4613426fc6f539cb4bc2556377a8e3350a1068524283d62",
    )

    # Verify this dataset/frontmatter tuple is in the context store
    assert (expected_dataset, expected_frontmatter) in [
        (dataset, documentation.frontmatter) for (dataset, documentation) in context_store.datasets
    ]

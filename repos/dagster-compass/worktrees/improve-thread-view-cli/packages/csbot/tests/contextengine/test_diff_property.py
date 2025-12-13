"""Property-based tests for ContextStore diff and apply operations using Hypothesis.

This module uses property-based testing to verify that compute_diff() and apply_diff()
are proper inverses of each other. The key property being tested is:

    For any two ContextStores v1 and v2:
    apply_diff(v1, compute_diff(v1, v2)) == v2

Hypothesis generates hundreds of random ContextStore pairs to try to find
counterexamples that violate this property.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from csbot.contextengine.diff import apply_diff, compute_diff
from tests.factories.context_store_factory import context_store_builder


# Helper strategies for generating valid values
def valid_text(min_size=1, max_size=50):
    """Generate valid text that works in YAML and filenames."""
    return st.text(
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), min_codepoint=32, max_codepoint=126
        ),
        min_size=min_size,
        max_size=max_size,
    ).filter(lambda s: s.strip() and not s.startswith("."))


def valid_cron_expression():
    """Generate valid cron expressions."""
    return st.sampled_from(
        [
            "0 * * * *",  # Every hour
            "0 0 * * *",  # Daily at midnight
            "0 0 * * 0",  # Weekly on Sunday
            "0 9 * * 1-5",  # Weekdays at 9am
            "*/15 * * * *",  # Every 15 minutes
        ]
    )


@st.composite
def context_store_strategy(draw):
    """Generate arbitrary ContextStore instances.

    This strategy builds ContextStores with random combinations of:
    - Project configuration
    - Datasets (0-5)
    - General context entries (0-3)
    - General cronjobs (0-3)
    - Channels (0-3) with their own context and cronjobs
    """
    builder = context_store_builder()

    # Always need a project
    # TODO test v1/v2
    builder = builder.with_project("test/test")

    # Optionally add teams
    if draw(st.booleans()):
        num_teams = draw(st.integers(min_value=1, max_value=3))
        teams = {}
        for _ in range(num_teams):
            team_name = draw(valid_text(min_size=3, max_size=15))
            num_members = draw(st.integers(min_value=1, max_value=3))
            members = [draw(valid_text(min_size=5, max_size=20)) for _ in range(num_members)]
            teams[team_name] = members
        builder = builder.with_project_teams(teams)

    # Randomly add system prompt
    if draw(st.booleans()):
        system_prompt = draw(st.text(min_size=10, max_size=200))
        builder = builder.with_system_prompt(system_prompt)

    # Randomly add datasets (0-5)
    num_datasets = draw(st.integers(min_value=0, max_value=5))
    for i in range(num_datasets):
        connection = draw(valid_text(min_size=3, max_size=15))
        table = draw(valid_text(min_size=3, max_size=20))
        markdown = draw(st.text(min_size=10, max_size=300))

        builder = builder.add_dataset(connection, f"{table}_{i}")  # Add index to ensure uniqueness
        builder = builder.with_markdown(markdown)

        # Optionally add schema hash
        if draw(st.booleans()):
            schema_hash = draw(
                st.text(
                    min_size=32,
                    max_size=64,
                    alphabet=st.characters(whitelist_categories=("Ll", "Nd")),
                )
            )
            columns = [
                draw(valid_text()) for _ in range(draw(st.integers(min_value=1, max_value=5)))
            ]
            builder = builder.with_schema_hash(schema_hash, columns)

    # Randomly add general context entries (0-3)
    num_context = draw(st.integers(min_value=0, max_value=3))
    for i in range(num_context):
        group = draw(valid_text(min_size=3, max_size=15))
        name = draw(valid_text(min_size=3, max_size=20))
        topic = draw(st.text(min_size=5, max_size=100))
        incorrect = draw(st.text(min_size=5, max_size=200))
        correct = draw(st.text(min_size=5, max_size=200))
        keywords = draw(st.text(min_size=5, max_size=100))

        builder = (
            builder.add_general_context(group, f"{name}_{i}")  # Ensure uniqueness
            .with_topic(topic)
            .with_incorrect(incorrect)
            .with_correct(correct)
            .with_keywords(keywords)
        )

    # Randomly add general cronjobs (0-3)
    num_cronjobs = draw(st.integers(min_value=0, max_value=3))
    for i in range(num_cronjobs):
        name = draw(valid_text(min_size=3, max_size=20))
        cron = draw(valid_cron_expression())
        question = draw(st.text(min_size=10, max_size=200))
        thread = draw(st.text(min_size=5, max_size=100))

        builder = (
            builder.add_general_cronjob(f"{name}_{i}")  # Ensure uniqueness
            .with_cron(cron)
            .with_question(question)
            .with_thread(thread)
        )

    # Randomly add channels (0-3)
    num_channels = draw(st.integers(min_value=0, max_value=3))
    for i in range(num_channels):
        channel_name = draw(valid_text(min_size=3, max_size=20))
        builder = builder.new_channel(f"{channel_name}_{i}")  # Ensure uniqueness

        # Maybe add channel system prompt
        if draw(st.booleans()):
            channel_prompt = draw(st.text(min_size=10, max_size=200))
            builder = builder.with_channel_system_prompt(channel_prompt)

        # Maybe add channel cronjobs (0-2)
        num_channel_cronjobs = draw(st.integers(min_value=0, max_value=2))
        for j in range(num_channel_cronjobs):
            job_name = draw(valid_text(min_size=3, max_size=15))
            cron = draw(valid_cron_expression())
            question = draw(st.text(min_size=10, max_size=150))
            thread = draw(st.text(min_size=5, max_size=80))

            builder = (
                builder.add_channel_cronjob(f"{job_name}_{j}")
                .with_cron(cron)
                .with_question(question)
                .with_thread(thread)
            )

        # Maybe add channel context (0-2)
        num_channel_context = draw(st.integers(min_value=0, max_value=2))
        for j in range(num_channel_context):
            group = draw(valid_text(min_size=3, max_size=15))
            name = draw(valid_text(min_size=3, max_size=15))
            topic = draw(st.text(min_size=5, max_size=100))
            incorrect = draw(st.text(min_size=5, max_size=150))
            correct = draw(st.text(min_size=5, max_size=150))
            keywords = draw(st.text(min_size=5, max_size=80))

            builder = (
                builder.add_channel_context(group, f"{name}_{j}")
                .with_topic(topic)
                .with_incorrect(incorrect)
                .with_correct(correct)
                .with_keywords(keywords)
            )

    return builder.build()


@given(
    v1=context_store_strategy(),
    v2=context_store_strategy(),
)
@settings(max_examples=100, deadline=None)
def test_diff_roundtrip_property(v1, v2):
    """Property test: Applying the diff between v1 and v2 to v1 should produce v2.

    This tests that compute_diff() and apply_diff() are proper inverses.
    For any two ContextStores v1 and v2:
        apply_diff(v1, compute_diff(v1, v2)) == v2

    Hypothesis will generate 100 random pairs of ContextStores to verify this property.
    """
    diff = compute_diff(v1, v2)
    reconstructed = apply_diff(v1, diff)

    assert reconstructed == v2, (
        f"Roundtrip failed!\nExpected: {v2}\nGot: {reconstructed}\nDiff: {diff}"
    )


@given(store=context_store_strategy())
@settings(max_examples=50, deadline=None)
def test_diff_identity_property(store):
    """Property test: Diff of identical stores should produce no changes when applied.

    For any ContextStore v:
        apply_diff(v, compute_diff(v, v)) == v
    """
    diff = compute_diff(store, store)

    # Diff should have no changes
    assert not diff.has_changes(), f"Diff of identical stores should be empty, got: {diff}"

    # Applying empty diff should return same store
    result = apply_diff(store, diff)
    assert result == store


@given(
    v1=context_store_strategy(),
    v2=context_store_strategy(),
    v3=context_store_strategy(),
)
@settings(max_examples=50, deadline=None)
def test_diff_composition_property(v1, v2, v3):
    """Property test: Applying multiple diffs should be associative.

    For any ContextStores v1, v2, v3:
        apply_diff(v1, diff(v1, v2), diff(v2, v3)) should produce v3
    """
    diff_1_to_2 = compute_diff(v1, v2)
    diff_2_to_3 = compute_diff(v2, v3)

    # Apply both diffs in sequence
    result = apply_diff(v1, diff_1_to_2, diff_2_to_3)

    # Should end up at v3
    assert result == v3, f"Composition failed!\nExpected: {v3}\nGot: {result}"


# Targeted tests for specific operations


@given(
    base=context_store_strategy(),
    dataset_connection=valid_text(min_size=3, max_size=15),
    dataset_table=valid_text(min_size=3, max_size=20),
    markdown=st.text(min_size=10, max_size=200),
)
@settings(max_examples=50, deadline=None)
def test_add_dataset_roundtrip(base, dataset_connection, dataset_table, markdown):
    """Property test: Adding a dataset should roundtrip correctly."""
    v1 = base
    v2 = (
        context_store_builder().with_project(base.project.project_name)
        # Copy all from base (simplified - just test adding one dataset to empty)
    )

    # Build v2 with an additional dataset
    builder = context_store_builder().with_project(base.project.project_name)
    builder = builder.add_dataset(dataset_connection, dataset_table).with_markdown(markdown)
    v2 = builder.build()

    diff = compute_diff(v1, v2)
    reconstructed = apply_diff(v1, diff)

    # Check that the new dataset exists in reconstructed
    reconstructed_tables = {(d[0].connection, d[0].table_name) for d in reconstructed.datasets}
    assert (dataset_connection, dataset_table) in reconstructed_tables


@given(
    base=context_store_strategy(),
    channel_name=valid_text(min_size=3, max_size=20),
    cronjob_name=valid_text(min_size=3, max_size=15),
    cron=valid_cron_expression(),
    question=st.text(min_size=10, max_size=150),
    thread=st.text(min_size=5, max_size=80),
)
@settings(max_examples=50, deadline=None)
def test_add_channel_cronjob_roundtrip(base, channel_name, cronjob_name, cron, question, thread):
    """Property test: Adding a channel cronjob should roundtrip correctly."""
    v1 = context_store_builder().with_project("test/project").build()

    v2 = (
        context_store_builder()
        .with_project("test/project")
        .new_channel(channel_name)
        .add_channel_cronjob(cronjob_name)
        .with_cron(cron)
        .with_question(question)
        .with_thread(thread)
        .build()
    )

    diff = compute_diff(v1, v2)
    reconstructed = apply_diff(v1, diff)

    assert reconstructed == v2, (
        f"Channel cronjob roundtrip failed!\n"
        f"Expected channels: {v2.channels}\n"
        f"Got channels: {reconstructed.channels}"
    )


@given(
    cronjob_name=valid_text(min_size=3, max_size=15),
    cron=valid_cron_expression(),
    question=st.text(min_size=10, max_size=150),
    thread=st.text(min_size=5, max_size=80),
)
@settings(max_examples=50, deadline=None)
def test_add_general_cronjob_roundtrip(cronjob_name, cron, question, thread):
    """Property test: Adding a general cronjob should roundtrip correctly."""
    v1 = context_store_builder().with_project("test/project").build()

    v2 = (
        context_store_builder()
        .with_project("test/project")
        .add_general_cronjob(cronjob_name)
        .with_cron(cron)
        .with_question(question)
        .with_thread(thread)
        .build()
    )

    diff = compute_diff(v1, v2)
    reconstructed = apply_diff(v1, diff)

    assert reconstructed == v2


@given(
    group=valid_text(min_size=3, max_size=15),
    name=valid_text(min_size=3, max_size=15),
    topic=st.text(min_size=5, max_size=100),
    incorrect=st.text(min_size=5, max_size=150),
    correct=st.text(min_size=5, max_size=150),
    keywords=st.text(min_size=5, max_size=80),
)
@settings(max_examples=50, deadline=None)
def test_add_general_context_roundtrip(group, name, topic, incorrect, correct, keywords):
    """Property test: Adding general context should roundtrip correctly."""
    v1 = context_store_builder().with_project("test/project").build()

    v2 = (
        context_store_builder()
        .with_project("test/project")
        .add_general_context(group, name)
        .with_topic(topic)
        .with_incorrect(incorrect)
        .with_correct(correct)
        .with_keywords(keywords)
        .build()
    )

    diff = compute_diff(v1, v2)
    reconstructed = apply_diff(v1, diff)

    assert reconstructed == v2


# Simplified property test with smaller examples for faster debugging
@given(
    v1=context_store_strategy(),
    v2=context_store_strategy(),
)
@settings(
    max_examples=200,  # Run 200 random examples
    deadline=None,  # No time limit per test
    print_blob=True,  # Print the failing example on failure
)
def test_full_diff_roundtrip_property(v1, v2):
    """Main property test: Full roundtrip for arbitrary ContextStore pairs.

    This is the primary property test that verifies compute_diff() and apply_diff()
    are proper inverses for ALL possible ContextStore combinations.

    Hypothesis will:
    1. Generate 200 random (v1, v2) pairs
    2. Test that apply_diff(v1, compute_diff(v1, v2)) == v2
    3. If it finds a failure, shrink it to the minimal failing case
    4. Report the minimal counterexample
    """
    diff = compute_diff(v1, v2)
    reconstructed = apply_diff(v1, diff)

    # The fundamental property: roundtrip should preserve v2
    assert reconstructed == v2, (
        f"\n{'=' * 80}\n"
        f"ROUNDTRIP PROPERTY VIOLATED\n"
        f"{'=' * 80}\n"
        f"\nOriginal v1:\n{v1}\n"
        f"\nTarget v2:\n{v2}\n"
        f"\nComputed diff:\n{diff}\n"
        f"\nReconstructed:\n{reconstructed}\n"
        f"\n{'=' * 80}\n"
        f"Differences:\n"
        f"  - Expected {len(v2.datasets)} datasets, got {len(reconstructed.datasets)}\n"
        f"  - Expected {len(v2.general_context)} context, got {len(reconstructed.general_context)}\n"
        f"  - Expected {len(v2.general_cronjobs)} cronjobs, got {len(reconstructed.general_cronjobs)}\n"
        f"  - Expected {len(v2.channels)} channels, got {len(reconstructed.channels)}\n"
        f"{'=' * 80}\n"
    )


# Example-based tests to complement property tests
def test_simple_examples():
    """Sanity check: Test a few simple hand-crafted examples."""
    # Empty to empty
    v1 = context_store_builder().with_project("test/project").build()
    v2 = context_store_builder().with_project("test/project").build()
    assert apply_diff(v1, compute_diff(v1, v2)) == v2

    # Add one dataset
    v1 = context_store_builder().with_project("test/project").build()
    v2 = context_store_builder().with_project("test/project").add_dataset("conn", "table").build()
    assert apply_diff(v1, compute_diff(v1, v2)) == v2

    # Add one cronjob
    v1 = context_store_builder().with_project("test/project").build()
    v2 = (
        context_store_builder()
        .with_project("test/project")
        .add_general_cronjob("job1")
        .with_cron("0 * * * *")
        .with_question("Q?")
        .with_thread("T")
        .build()
    )
    assert apply_diff(v1, compute_diff(v1, v2)) == v2

    # Add one channel
    v1 = context_store_builder().with_project("test/project").build()
    v2 = context_store_builder().with_project("test/project").new_channel("chan1").build()
    assert apply_diff(v1, compute_diff(v1, v2)) == v2

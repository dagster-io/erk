from csbot.contextengine.diff import apply_diff, compute_diff
from tests.factories.context_store_factory import context_store_builder


def test_add_dataset():
    v1 = context_store_builder().build()
    v2 = context_store_builder().add_dataset("x", "y").build()
    assert apply_diff(v1, compute_diff(v1, v2)) == v2


def test_add_team():
    v1 = context_store_builder().build()
    v2 = context_store_builder().with_project_teams({"x": ["y"]}).build()
    assert apply_diff(v1, compute_diff(v1, v2)) == v2


def test_team_modified():
    v1 = context_store_builder().with_project_teams({"x": ["y"]}).build()
    v2 = context_store_builder().with_project_teams({"x": ["y", "z"]}).build()
    assert apply_diff(v1, compute_diff(v1, v2)) == v2


def test_add_cronjob():
    v1 = context_store_builder().build()
    v2 = context_store_builder().add_general_cronjob("x", "* * * * *", "y", "z").build()
    assert apply_diff(v1, compute_diff(v1, v2)) == v2


def test_add_channel_cronjob():
    v1 = context_store_builder().build()
    v2 = (
        context_store_builder()
        .new_channel("x")
        .add_channel_cronjob("x", "* * * * *", "y", "z")
        .build()
    )
    assert apply_diff(v1, compute_diff(v1, v2)) == v2

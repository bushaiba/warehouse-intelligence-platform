from warehouse_intelligence.synthetic import generate_events


def test_generator_is_repeatable():
    first = generate_events(count=25, seed=7)
    second = generate_events(count=25, seed=7)
    assert [row.model_dump() for row in first] == [row.model_dump() for row in second]


def test_generator_creates_requested_count():
    assert len(generate_events(count=123, seed=1)) == 123

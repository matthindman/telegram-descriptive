from telegram_descriptive.reporting.exports import suppress_small_counts, write_csv


def test_suppress_small_counts_marks_suppressed_cells():
    rows = suppress_small_counts([{"label": "x", "count": 3, "n_total": 10}], min_cell_count=5)

    assert rows == [{"label": "x", "count": None, "n_total": 10, "count_suppressed": True}]


def test_write_csv_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "out.csv"

    write_csv([{"b": 2, "a": 1}], str(path))

    assert path.read_text(encoding="utf-8").splitlines() == ["a,b", "1,2"]

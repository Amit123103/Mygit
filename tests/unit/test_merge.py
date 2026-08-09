from mygit_core.merge import merge_3way_file


def test_3way_merge_clean():
    base = "line1\nline2\nline3\n"
    ours = "line1\nline2_modified\nline3\n"
    theirs = "line1\nline2\nline3\n"

    has_conflict, result = merge_3way_file(base, ours, theirs)
    assert not has_conflict
    assert result == "line1\nline2_modified\nline3\n"


def test_3way_merge_conflict():
    base = "line1\nline2\nline3\n"
    ours = "line1\nline2_ours\nline3\n"
    theirs = "line1\nline2_theirs\nline3\n"

    has_conflict, result = merge_3way_file(base, ours, theirs)
    assert has_conflict
    assert "<<<<<<< OURS" in result
    assert ">>>>>>> THEIRS" in result

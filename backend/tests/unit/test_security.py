from app.security import is_safe_dbname, is_safe_metric_id, is_safe_project_id


def test_project_id_ok():
    assert is_safe_project_id("fa.wikipedia")
    assert is_safe_project_id("commons.wikimedia")
    assert is_safe_project_id("wikidata")


def test_project_id_bad():
    assert not is_safe_project_id("../etc/passwd")
    assert not is_safe_project_id("fa wikipedia")
    assert not is_safe_project_id("fa;drop")
    assert not is_safe_project_id("")


def test_dbname_ok():
    assert is_safe_dbname("fawiki")
    assert is_safe_dbname("commonswiki")


def test_dbname_bad():
    assert not is_safe_dbname("fawiki;drop table")
    assert not is_safe_dbname("../x")
    assert not is_safe_dbname("fa-wiki")  # hyphen not allowed in our strict pattern
    assert not is_safe_dbname("")


def test_metric_id():
    assert is_safe_metric_id("editors.active")
    assert is_safe_metric_id("maintenance.open_total")
    assert not is_safe_metric_id("editors active")

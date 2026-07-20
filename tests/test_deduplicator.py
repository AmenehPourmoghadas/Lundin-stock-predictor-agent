from lundin_agent.deduplicator import deduplicate
from lundin_agent.models import Article

def test_duplicate_titles_are_removed():
    items = [
        Article("Lundin Mining reports production results", "a", "x", "", "Lundin", "test"),
        Article("Lundin Mining reports production results!", "b", "y", "", "Lundin", "test"),
    ]
    assert len(deduplicate(items)) == 1

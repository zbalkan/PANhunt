import pytest

from panhunt.exceptions import PANHuntException
from panhunt.scancontext import ResourceBudget, ScanContext, ScanLimits


def _root_context() -> ScanContext:
    limits = ScanLimits(max_depth=2, max_child_jobs=2, max_total_expanded_bytes=10)
    return ScanContext.root('/tmp/root.zip', limits, ResourceBudget(limits))


def test_child_context_tracks_logical_path_depth_and_chain():
    root = _root_context()

    child = root.child('child.txt', payload_size=4)

    assert child.logical_path == '/tmp/root.zip!/child.txt'
    assert child.depth == 1
    assert child.parent_archive == '/tmp/root.zip'
    assert child.container_chain == ['/tmp/root.zip']
    assert child.budget.expanded_bytes == 4
    assert child.budget.child_jobs == 1


def test_child_context_enforces_depth_limit():
    child = _root_context().child('inner.zip')
    grandchild = child.child('nested.zip')

    with pytest.raises(PANHuntException, match='Scan depth limit exceeded'):
        grandchild.child('too-deep.txt')


def test_child_context_enforces_child_job_limit():
    root = _root_context()
    root.child('one.txt')
    root.child('two.txt')

    with pytest.raises(PANHuntException, match='Scan child-job limit exceeded'):
        root.child('three.txt')


def test_child_context_enforces_expanded_byte_limit():
    root = _root_context()
    root.child('one.txt', payload_size=6)

    with pytest.raises(PANHuntException, match='Scan expanded-byte limit exceeded'):
        root.child('two.txt', payload_size=5)


def test_attachment_budget_tracks_decoded_bytes():
    root = _root_context()

    root.reserve_attachment('a.txt', 4)

    assert root.budget.attachment_bytes == 4


def test_attachment_budget_enforces_total_decoded_bytes():
    limits = ScanLimits(
        max_depth=2,
        max_child_jobs=2,
        max_total_expanded_bytes=10,
        max_attachment_size=10,
        max_attachments_per_message=2,
        max_total_attachment_bytes=5,
    )
    root = ScanContext.root('/tmp/root.eml', limits, ResourceBudget(limits))

    root.reserve_attachment('one.txt', 3)
    with pytest.raises(PANHuntException, match='decoded attachment-byte limit'):
        root.reserve_attachment('two.txt', 3)


def test_attachment_budget_enforces_per_message_count():
    limits = ScanLimits(
        max_depth=2,
        max_child_jobs=2,
        max_total_expanded_bytes=10,
        max_attachment_size=10,
        max_attachments_per_message=1,
        max_total_attachment_bytes=10,
    )
    root = ScanContext.root('/tmp/root.eml', limits, ResourceBudget(limits))

    with pytest.raises(PANHuntException, match='Attachment count limit exceeded'):
        root.reserve_attachment('two.txt', 1, attachment_count=2)

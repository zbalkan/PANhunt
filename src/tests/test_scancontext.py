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

"""Tests for PAN finder behavior."""

from panhunt.finder import PanFinder


def test_find_returns_empty_for_clean_text(config):
    finder = PanFinder(config)

    assert finder.find('clean text with 1234 and 5678 only') == []


def test_find_keeps_valid_pan_detection(config):
    finder = PanFinder(config)

    matches = finder.find('Payment reference: 4111 1111 1111 1111')

    assert [str(match) for match in matches] == ['Visa:411111******1111']

"""Tests for PAN finder behavior."""

from unittest.mock import MagicMock

from panhunt.finder import PanFinder


def test_find_skips_brand_regexes_when_text_has_too_few_digits(config):
    finder = PanFinder(config)
    finder._brands = [('Visa', MagicMock())]

    assert finder.find('clean text with 1234 and 5678 only') == []
    finder._brands[0][1].findall.assert_not_called()


def test_find_keeps_valid_pan_detection(config):
    finder = PanFinder(config)

    matches = finder.find('Payment reference: 4111 1111 1111 1111')

    assert [str(match) for match in matches] == ['Visa:411111******1111']

"""Regression tests for non-consuming card boundaries and supported lengths."""

from panhunt.patterns import CardPatterns


def _matches(brand: str, text: str) -> list[str]:
    pattern = dict(CardPatterns().brands())[brand]
    return pattern.findall(text)


def test_diners_and_discover_do_not_consume_neighboring_separator():
    assert _matches('DinersClub', 'x30569309025904;') == []
    assert _matches('DinersClub', ':30569309025904;') == ['30569309025904']
    assert _matches('Discover', ':6011111111111117;') == ['6011111111111117']


def test_right_boundary_rejects_adjacent_alphanumeric_or_extra_digit():
    assert not _matches('Discover', '6011111111111117x')
    assert not _matches('Visa', '4111111111111111_')
    assert not _matches('AMEX', '3782822463100059')


def test_visa_13_16_19_digit_lengths():
    for number in ('4222222222222', '4111111111111111', '4000000000000000006'):
        assert _matches('Visa', ':' + number + ';') == [number]


def test_amex_mixed_separators():
    assert _matches('AMEX', ':3782-822463 10005;') == ['3782-822463 10005']


def test_maestro_minimum_length_policy(tmp_path):
    from panhunt.config import ScanConfiguration
    from panhunt.finder import PanFinder

    candidate = '501800000009'  # 12 digits, valid Luhn
    strict = ScanConfiguration.from_args(target_path=str(tmp_path))
    permissive = ScanConfiguration.from_args(target_path=str(tmp_path), maestro_min_length=12)
    assert not PanFinder(strict).find(candidate)
    assert len(PanFinder(permissive).find(candidate)) == 1


def test_unicode_digits_not_classified_as_ascii_pan(tmp_path):
    from panhunt.config import ScanConfiguration
    from panhunt.finder import PanFinder

    config = ScanConfiguration.from_args(target_path=str(tmp_path))
    assert not PanFinder(config).find('４１１１１１１１１１１１１１１１')
    assert not PanFinder(config).find('411111111111111١')
    assert not PanFinder(config).find('４1111111111111111')
    assert not PanFinder(config).find('4111111111111111４')


def test_overlapping_schemes_have_one_reported_position(tmp_path):
    from panhunt.config import ScanConfiguration
    from panhunt.finder import PanFinder

    config = ScanConfiguration.from_args(target_path=str(tmp_path))
    offsets = PanFinder(config).find_with_offsets('payment 6221260000000000')
    assert len(offsets) <= 1

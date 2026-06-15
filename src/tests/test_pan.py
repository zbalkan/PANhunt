"""Tests for PAN class."""

import pytest

from panhunt.pan import PAN


class TestLuhnChecksum:
    def test_valid_visa(self):
        assert PAN.is_valid_luhn_checksum('4111111111111111') is True

    def test_valid_mastercard(self):
        assert PAN.is_valid_luhn_checksum('5500005555555559') is True

    def test_valid_amex(self):
        assert PAN.is_valid_luhn_checksum('371449635398431') is True

    def test_invalid_luhn(self):
        assert PAN.is_valid_luhn_checksum('4111111111111112') is False

    def test_strips_spaces(self):
        assert PAN.is_valid_luhn_checksum('4111 1111 1111 1111') is True

    def test_strips_dashes(self):
        assert PAN.is_valid_luhn_checksum('4111-1111-1111-1111') is True

    def test_sequential_digits_invalid(self):
        assert PAN.is_valid_luhn_checksum('1234567890123456') is False


class TestMasking:
    def test_str_shows_brand(self):
        p = PAN(brand='Visa', pan='4111111111111111')
        assert 'Visa' in str(p)

    def test_first_six_visible(self):
        p = PAN(brand='Visa', pan='4111111111111111')
        assert str(p).startswith('Visa:411111')

    def test_last_four_visible(self):
        p = PAN(brand='Visa', pan='4111111111111111')
        assert str(p).endswith('1111')

    def test_middle_digits_masked(self):
        p = PAN(brand='Visa', pan='4111111111111111')
        s = str(p)
        # between brand: prefix and last 4 there should be asterisks
        masked_part = s.split(':')[1]
        assert '*' in masked_part

    def test_spaces_stripped_in_mask(self):
        p = PAN(brand='Visa', pan='4111 1111 1111 1111')
        s = str(p)
        assert ' ' not in s.split(':')[1]

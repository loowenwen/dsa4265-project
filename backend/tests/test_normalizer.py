import unittest

from app.services.normalizer import (
    parse_currency,
    parse_integer,
    parse_months,
    parse_percentage,
)


class NormalizerTests(unittest.TestCase):
    def test_parse_currency(self) -> None:
        self.assertEqual(parse_currency("$42,000"), 42000.0)
        self.assertEqual(parse_currency("18k"), 18000.0)

    def test_parse_percentage(self) -> None:
        self.assertEqual(parse_percentage("46%"), 46.0)
        self.assertEqual(parse_percentage("46"), 46.0)
        self.assertIsNone(parse_percentage("0.46"))

    def test_parse_integer(self) -> None:
        self.assertEqual(parse_integer("2"), 2)
        self.assertEqual(parse_integer("two late payments"), 2)
        self.assertIsNone(parse_integer("2.5"))

    def test_parse_months(self) -> None:
        self.assertEqual(parse_months("8 months"), 8)
        self.assertEqual(parse_months("2 years"), 24)
        self.assertEqual(parse_months("6"), 6)


if __name__ == "__main__":
    unittest.main()

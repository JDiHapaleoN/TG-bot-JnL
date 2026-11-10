"""Unit tests for the 2-second transaction parser including negative and boundary checks."""

from decimal import Decimal
import unittest

from bot.services.parser import parse_transaction_message


class TestTransactionParser(unittest.TestCase):
    def test_simple_expense_integer(self):
        res = parse_transaction_message("5")
        self.assertIsNotNone(res)
        self.assertEqual(res.tx_type, "expense")
        self.assertEqual(res.amount, Decimal("5.00"))
        self.assertEqual(res.description, "")

    def test_decimal_dot_and_comma(self):
        res_dot = parse_transaction_message("12.50")
        self.assertIsNotNone(res_dot)
        self.assertEqual(res_dot.tx_type, "expense")
        self.assertEqual(res_dot.amount, Decimal("12.50"))

        res_comma = parse_transaction_message("12,50")
        self.assertIsNotNone(res_comma)
        self.assertEqual(res_comma.tx_type, "expense")
        self.assertEqual(res_comma.amount, Decimal("12.50"))

    def test_pipe_description(self):
        res = parse_transaction_message("5 | Обед в McDonald's")
        self.assertIsNotNone(res)
        self.assertEqual(res.tx_type, "expense")
        self.assertEqual(res.amount, Decimal("5.00"))
        self.assertEqual(res.description, "Обед в McDonald's")

    def test_space_description_examples_from_spec(self):
        res1 = parse_transaction_message("5 Обед")
        self.assertEqual(res1.tx_type, "expense")
        self.assertEqual(res1.amount, Decimal("5.00"))
        self.assertEqual(res1.description, "Обед")

        res2 = parse_transaction_message("25 Продукты")
        self.assertEqual(res2.tx_type, "expense")
        self.assertEqual(res2.amount, Decimal("25.00"))
        self.assertEqual(res2.description, "Продукты")

    def test_income_examples_from_spec(self):
        res1 = parse_transaction_message("+1500")
        self.assertEqual(res1.tx_type, "income")
        self.assertEqual(res1.amount, Decimal("1500.00"))
        self.assertEqual(res1.description, "")

        res2 = parse_transaction_message("+200 Стипендия")
        self.assertEqual(res2.tx_type, "income")
        self.assertEqual(res2.amount, Decimal("200.00"))
        self.assertEqual(res2.description, "Стипендия")

        res3 = parse_transaction_message("+50 Подарок")
        self.assertEqual(res3.tx_type, "income")
        self.assertEqual(res3.amount, Decimal("50.00"))
        self.assertEqual(res3.description, "Подарок")

    def test_default_type_income_without_plus(self):
        res = parse_transaction_message("1500 Зарплата", default_type="income")
        self.assertEqual(res.tx_type, "income")
        self.assertEqual(res.amount, Decimal("1500.00"))
        self.assertEqual(res.description, "Зарплата")

    def test_negative_and_invalid_inputs_rejected(self):
        self.assertIsNone(parse_transaction_message(""))
        self.assertIsNone(parse_transaction_message("   "))
        self.assertIsNone(parse_transaction_message("/start"))
        self.assertIsNone(parse_transaction_message("Просто текст без суммы"))
        self.assertIsNone(parse_transaction_message("0"))
        self.assertIsNone(parse_transaction_message("0.00"))
        self.assertIsNone(parse_transaction_message("-5"))
        self.assertIsNone(parse_transaction_message("-12.50 Обед"))
        self.assertIsNone(parse_transaction_message("−100"))
        self.assertIsNone(parse_transaction_message("12.345"))
        self.assertIsNone(parse_transaction_message("1000000000.00"))


if __name__ == "__main__":
    unittest.main()

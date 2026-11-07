import contextlib
from datetime import datetime
import io
import unittest
from unittest.mock import patch
import stripe
import main


class DateRangeTest(unittest.TestCase):
    def test_end_date_includes_full_day_across_month_and_year_boundaries(self):
        for start, end, exclusive in [
            (datetime(2026, 10, 1), datetime(2026, 10, 31), datetime(2026, 11, 1)),
            (datetime(2026, 12, 31), datetime(2026, 12, 31), datetime(2027, 1, 1)),
            (datetime(2028, 2, 1), datetime(2028, 2, 29), datetime(2028, 3, 1)),
        ]:
            with self.subTest(end=end), patch.object(stripe.BalanceTransaction, 'list') as query, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                query.return_value.auto_paging_iter.return_value = iter([])
                main.fetch_balance_transactions(start, end)
                query.assert_called_once_with(
                    created={'gte': int(start.timestamp()), 'lt': int(exclusive.timestamp())},
                    limit=100,
                )

#!/usr/bin/env python3
"""A separate, predeclared timeout comparison on the original full uint32 pair."""
import sys

import run_scaling


def protocol():
    return dict(label='POPCOUNT BUDGET', title='Popcount：32 位域的查询时间预算比较',
                prefix='budget-', workdir='.verify-equiv-runs/popcount-budget', guide='BUDGET.md',
                changed='Only per-query timeout: 30 versus 120 seconds; full uint32 domain and 300-second/96-query discovery limits unchanged',
                rows=[dict(name=f'r{repeat}-t{timeout}', repeat=repeat, width=32, query_timeout=timeout)
                      for repeat, timeout in ((1, 30), (1, 120), (2, 120), (2, 30))])


def main(argv=None):
    return run_scaling.main(argv, protocol=protocol())


if __name__ == '__main__':
    sys.exit(main())

import optimize
import positions
import pytest


def test_all():
    optimize.optimize_svgs()
    positions.generate_positions()

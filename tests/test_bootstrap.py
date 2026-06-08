import pytest

from telegram_descriptive.estimation.bootstrap import bootstrap_interval


def test_bootstrap_interval_rejects_invalid_alpha():
    with pytest.raises(ValueError, match="alpha"):
        bootstrap_interval([1, 2, 3], statistic=sum, alpha=1.0)

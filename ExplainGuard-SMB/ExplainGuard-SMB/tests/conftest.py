import pytest

from explainguard.generator import GeneratorConfig, generate


@pytest.fixture(scope="session")
def small_cfg():
    return GeneratorConfig(seed=3, days=40, n_customers=500, n_merchants=10, n_rings=4,
                           n_card_testing_bursts=6, n_takeovers=30)


@pytest.fixture(scope="session")
def small_df(small_cfg):
    return generate(small_cfg)

import pytest

from sentinel.demo import generate_demo
from sentinel.evaluation import temporal_split
from sentinel.model import Detector, ModelConfig


@pytest.fixture(scope="session")
def dataset():
    return generate_demo(seed=42, days=15, events_per_day=60)


@pytest.fixture(scope="session")
def splits(dataset):
    return temporal_split(dataset)


@pytest.fixture(scope="session")
def detector(splits):
    return Detector(ModelConfig(trees=50)).fit(splits[0], splits[1])

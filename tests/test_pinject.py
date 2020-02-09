from loguru import logger
import inject
import pytest


class InnerClass(object):
    def __init__(self):
        self.forty_two = 42

    def __del__(self):
        logger.info(f'{self=} is deleted')


class OuterClass(object):
    inner_class = inject.attr(InnerClass)

    def __init(self, inner_class):
        self.inner_class = inner_class

    def __del__(self):
        logger.info(f'{self=} is deleted')


@pytest.fixture(autouse=True)
def context(capsys):
    with capsys.disabled():
        logger.debug('configure injector')

        yield

        logger.debug('clean up injector')


def test_inject():
    inject.configure()
    o = OuterClass()
    assert o.inner_class.forty_two == 42
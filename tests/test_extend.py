# Maintainer:     Ryan Young
# Last Modified:  Dec 01, 2022
import doctest
import inspect
import pytest
from pandas import DataFrame, Series
from extend_inplace import (
    Extend,
    ExistingAttributeError,
)


option_combinations = [
    (False, False, False),
    (False, False, True),
    (False, True, True),
    (True, True, True),
    (True, True, False),
    (True, False, False),
    (True, False, True),
    (False, True, False),
]
@pytest.mark.parametrize('overwrite, keep, as_property', option_combinations)
def test_options_dec_function(overwrite, keep, as_property):

    @Extend(DataFrame, overwrite=overwrite, keep=keep, as_property=as_property)
    def a(self): ...

    assert True

@pytest.mark.parametrize('overwrite, keep, as_property', option_combinations)
def test_options_dec_class(overwrite, keep, as_property):

    @Extend(DataFrame, overwrite=overwrite, keep=keep, as_property=as_property)
    class _:
        def a(self): ...

    assert True

@pytest.mark.parametrize('overwrite, keep, as_property', option_combinations)
def test_options_subclass(overwrite, keep, as_property):

    class _(Extend, DataFrame, overwrite=overwrite, keep=keep, as_property=as_property):
        def a(self): ...

    assert True


arg_combinations_dec = [
    ([ DataFrame ]),
    ([ (DataFrame,) ]),
    ([ [DataFrame, Series] ]),
    ([ DataFrame, [Series] ]),
]

@pytest.mark.parametrize('args', arg_combinations_dec)
def test_args_dec(args):
    args = tuple(args)
    @Extend(*args)
    def a(self): ...

    @Extend(*args)
    class _:
        def a(self): ...

    if len(args) == 1:
        args = args[0]

    class _(Extend, to = args):
        def a(self): ...

    assert True


def test_inner_cls():
    @Extend(DataFrame)
    class _:
        class A:
            @classmethod
            def a(cls):
                return "a"

    class _(Extend, DataFrame):
        class B:
            @classmethod
            def b(cls):
                return "b"

    df = DataFrame()
    assert df.A.a() == "a"
    assert df.B.b() == "b"


def test_property():

    @Extend(DataFrame)
    @property
    def one(self): return 1

    @Extend(DataFrame)
    class _:
        @property
        def two(self): return 2

    class _(Extend, DataFrame):
        @property
        def three(self): return 3

    df = DataFrame()
    assert df.one == 1
    assert df.two == 2
    assert df.three == 3


def test_as_property():
    @Extend(DataFrame, as_property=True)
    class _:
        def nrows(self):
            return self.shape[0]

    df = DataFrame()
    assert df.nrows == 0


def test_bad_as_property():
    with pytest.raises(TypeError):
        @Extend(DataFrame, as_property=True)
        class _:
            class cant_be_property:
                ...

    with pytest.raises(ValueError):
        @Extend(DataFrame, as_property=True)
        def bad_prop(self, something_else):
            ...


def test_bad_args():
    with pytest.raises(TypeError):
        @Extend(DataFrame, 5)
        def a(self): ...


def test_other_types():

    @Extend(DataFrame)
    @classmethod
    def show_name(cls):
        return cls.__name__

    @Extend(DataFrame)
    @staticmethod
    def static(pass_something):
        return pass_something

    assert DataFrame.show_name() == "DataFrame"
    assert DataFrame.static('hi') == 'hi'


def test_args_cls():
    class _(Extend, DataFrame):
        def a(self): ...

    class _(Extend, DataFrame, Series):
        def a(self): ...

# EXPECT EXCEPTIONS

def test_bad_subclass():
    with pytest.raises(ValueError):
        class _(DataFrame, Extend):
            def a(self): ...

    with pytest.raises(ValueError):
        class _(Extend):
            def a(self): ...

    assert True


def test_bad_dec():
    with pytest.raises(ValueError):
        @Extend()
        class _:
            def a(self): ...


def test_existing_attr():
    with pytest.raises(ExistingAttributeError):
        @Extend(DataFrame)
        def shape(self):
            return 'shape'

    @Extend(DataFrame, overwrite=True)
    def shape(self):
        return 'shape'

    df = DataFrame()
    assert df.shape() == "shape"


def test_keep():
    @Extend(DataFrame)
    def a(self):
        return

    assert locals().get('a') is None

    @Extend(DataFrame, keep=True)
    def a(self):
        return

    assert not locals().get('a') is None


def test_history():
    # No error should be thrown if replacing a user-defined attribute
    @Extend(DataFrame)
    class _:
        def nonsense(self):
            return

    @Extend(DataFrame)
    class _:
        def nonsense(self):
            return


def main_():
    import pandas as pd

    @Extend(DataFrame, keep=True)
    def a(self):
        return

    assert locals().get('a') is not None

    print(locals())





if __name__ == "__main__":
    main_()

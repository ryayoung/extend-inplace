"""
This simple mini-framework is built for interactive notebook workflows where the
bulk of the user's code relies on large, object-oriented, external libraries
such as pandas. Its purpose is to enable/enforce consistent, readable, safe, and
concise code when writing user-defined functions that interact with large, complex
classes imported from external libraries.

The goal of this project is simple: allow the user to directly modify imported
classes within their code in a concise, expressive, safe, and readable way.

Its primary use-case is dataframe-centric workflows (pandas, pyspark, polars, etc.)
in which method-chaining is often desired over standalone function calls. Most of
the examples presented throughout this module use ``pandas``, but the concepts apply
to any similar package.

*The problem:*
------------

Defining custom functions is a critical step in any workflow. Unfortunately, in a
dataframe-centric, notebook workflow described above, standalone custom functions
can often make code messier than desired. And sometimes we avoid creating a
desired function because the resulting break in our pretty method-chained code
formatting outweighs the potential saved space, or because it would require
creating unnecessary extra variables.

Sometimes it's just nice to change how an object works.

>>> import pandas as pd
>>> from numpy import NaN
>>> df = pd.DataFrame({'a': [1,2,3], 'b': [4,5,NaN], 'c': [10,20,30]})
>>> sr = pd.Series([1,2,3,4,5])

Say you want ``pd.DataFrame`` and ``pd.Series`` to have an ``nrows`` property.

>>> @property
>>> def nrows(self):
>>>     return self.shape[0]
>>> setattr(pd.DataFrame, 'nrows', nrows)
>>> setattr(pd.Series, 'nrows', nrows)
>>> df.nrows
3

There are serious problems with this code:
1.  The reader doesn't know which class ``nrows`` will be a property of until they
    reach the bottom of the declaration. In larger code blocks, this is annoying.
2.  The ``setattr()`` calls are repetitive and occupy more space than the function!
3.  It's redundant, hard to refactor, and creates room for error. The function
    name is written 5 times, instead of 1.

Instead...

>>> @inject(pd.DataFrame, pd.Series)
>>> @property
>>> def nrows(self):
>>>     return self.shape[0]

Or, wrap multiple functions in a 'fake' class. This also allows for injection of
class variables, since decorators can't work on variables directly.

>>> @inject(pd.DataFrame)
>>> class _:
>>>     SOME_CONSTANT = 5
>>>     @property
>>>     def nrows(self):
>>>         return self.shape[0]
>>>     @property
>>>     def ncols(self):
>>>         return self.shape[1]
>>> df.nrows, df.ncols
(3, 3)
>>> pd.DataFrame.SOME_CONSTANT
5

Injected classes can also be declared in a 1-liner

>>> class _(Inject, to = pd.DataFrame):
>>>     ...

In the unusual case of needing to define many properties quickly, we can save
some space on decorators with ``as_property=True``, as long as all the attributes
are functions that take a single positional param

>>> class _(Inject, to = pd.DataFrame, as_property=True):
>>>     def nrows(self):
>>>         return self.shape[0]
>>>     def ncols(self):
>>>         return self.shape[1]
>>> df.nrows, df.ncols
(3, 3)

As a safeguard against accidentally/unknowingly replacing existing attributes, an error
is thrown by default if an overwrite is attempted. Bypass this with ``overwrite=True``

>>> @inject(pd.DataFrame)
>>> def shape(self):
>>>     ...
Traceback (most recent call last):
 ...
ExistingAttributeError: pandas.core.frame.DataFrame.shape already exists.
Pass `overwrite = True` to avoid this error.
>>> @inject(pd.DataFrame, overwrite=True)
>>> def shape(self):
>>>     ... # success


Notes
-----
The ``ExistingAttributeError`` validation ignores custom injected attributes
(by recording a globally persistent history) when checking if an attribute
already exists. This allows notebook users to repeatedly execute cells without
raising errors against the attributes they just defined.

"""

<h1> extend-inplace &nbsp;&nbsp;&nbsp; <a href="https://pypi.org/project/extend-inplace/" alt="Version"> <img src="https://img.shields.io/pypi/v/extend-inplace.svg" /></a> &nbsp;&nbsp;&nbsp; <a href="https://github.com/ryayoung/extend-inplace/actions"> <img src="https://github.com/ryayoung/extend-inplace/actions/workflows/tests.yaml/badge.svg"/> </a> </h1>

```text
pip install extend-inplace
```

---

A simple tool to enable an unconventional but sometimes useful coding style. In simple terms, it's a framework for modifying existing classes in an easy, organized, and readable way. I'll explain why this exists shortly. First, see the below examples.

<table>
<tr>
<td colspan="3">On the left is your code. On the right is how it's interpreted at runtime</td>
<tr>
<tr>
<td><img width="350" alt="example3" src="https://user-images.githubusercontent.com/90723578/205125281-4168cbe4-43d0-45e6-9bc7-9d900f22b611.png"></td>
<td><img width="350" alt="example1" src="https://user-images.githubusercontent.com/90723578/205125276-aac7b2bc-5474-4278-be51-9f5640957197.png"></td>
<td><img width="350" alt="example2" src="https://user-images.githubusercontent.com/90723578/205125280-ab887b5f-774b-433c-a227-df37710b51b1.png"></td>
</tr>
</table>

Elements under `@Extend` and `class _(Extend` get 'moved' to `Something` (they become `None` in global scope and set as attributes on `Something`).

---

<br>

## Why does this exist? Why not extend with a child class?

I built this tool for use in notebook workflows where the majority of code is centered around instances of large, complex classes imported from external libraries, such as pandas/spark `DataFrame`, numpy `ndarray`, or objects of other dataframing libraries, where method chaining is a common practice.

When defining functions in your workflow to manipulate objects of these classes, we usually define them as standalone functions that take an object as an parameter. However, this might be annoying if the rest of our code is using method chaining on the objects.

Creating a child class with extended functionality is always considered best practice. But sometimes this can be inconvenient in a fast-paced or experimental working environment. For instance, you could could subclass pandas `DataFrame`, but `pd.read_csv()` will still return a standard `DataFrame` which you'll need to cast to your new type. And you could subclass pandas `Series`, but selecting columns from `DataFrame` will still return a standard `Series`. This can easily introduce bugs and add unwanted complexity to your code.

## Why not just use `setattr()`?

Here's a simple example. Say for some stupid reason you want `pd.DataFrame` and `pd.Series` to have an `nrows` property with the number of rows.

```py
>>> @property
... def nrows(self):
...     return self.shape[0]
...
>>> setattr(pd.DataFrame, 'nrows', nrows)
>>> setattr(pd.Series, 'nrows', nrows)
>>> df.nrows # assume we've already defined df = pd.DataFrame()
3
```

#### There are serious problems with this code:
1.  The reader doesn't know which class ``nrows`` will be a property of until they
    reach the bottom of the declaration. In larger code blocks, this is annoying.
2.  The ``setattr()`` calls are repetitive and occupy more space than the function!
3.  It's redundant, hard to refactor, and creates room for error. The function
    name is written **5 TIMES**, instead of 1.

Instead...
```py
>>> @Extend(pd.DataFrame, pd.Series)
... @property
... def nrows(self):
...     return self.shape[0]
...
```

The above code is concise and easy to read. If we look more closely at what happened...

```py
>>> pd.DataFrame.nrows
<property object at 0x1025a3560>
>>> print(globals()['nrows'])
None
```

`nrows` no now `None` in the global scope, and is instead a property of `DataFrame`

#

# How to use
---

By now you've seen what happens when we decorate a function or property with `Extend`.

But we can also set a *group* of attributes without repeated use of `@Extend`.

To do this, nest your attributes in a 'fake' container class.

```py
>>> @Extend(pd.DataFrame)
... class _:
...     SOME_CONSTANT = 5
...     @property
...     def nrows(self):
...         return self.shape[0]
...     def say_hello(self):
...         return "Hello"
...
>>> df.nrows
0
>>> df.say_hello()
'Hello'
```

This can also be expressed more concisely as ...

```py
>>> class _(Extend, to = [pd.DataFrame]):
...     ... # attributes go here
```

If you thought it couldn't get any more concise, it can! The above can also be written as ...

```py
>>> class _(Extend, pd.DataFrame):
...     ...
```

While more concise, the above code is less intuitive because there is some metaclass magic going on.

While this looks like multiple inheritance, **IT IS NOT.** The metaclass of `Extend` knows that all types
passed after `Extend` should be treated as targets, not parents.

#

## Additional functionality

---

### Protection against accidental replacement of existing attributes

`override`: bool, default False

By default, `Extend` has a safety net in place to prevent replacing existing attributes

```py
>>> @Extend(pd.DataFrame)
... def shape(self): # DataFrame already has this
...     ...
...
Traceback (most recent call last):
 ...
ExistingAttributeError: pandas.core.frame.DataFrame.shape already exists.
Pass `overwrite = True` to avoid this error.
```
```py
>>> @Extend(pd.DataFrame, overwrite=True)
... def shape(self):
...     ...
...
```

Great, but does that mean I'll get an error every time i re-run a notebook cell, since my attributes
will now exist in the class? Nope. A history of user-defined attributes is recorded in in the global
scope. These will be ignored at validation.

```py
>>> @Extend(pd.DataFrame)
... def foo(self):
...     ...
...
>>> @Extend(pd.DataFrame)
... def foo(self):
...     ...
...
>>>
```

# 

### Prevent elements from being removed from global scope
`keep`: bool, Default False

Earlier, we saw that a decorated function became `None` in `globals()` after declaration.

This can be prevented...

```py
>>> @Extend(pd.DataFrame, keep=True)
... def foo(self):
...     ...
...
>>> print(globals()['foo'])
<function foo at 0x11bbbf060>
```

#

### Concisely define a group of properties
`as_property`: bool, defualt False

In the unusual case where you want to define many properties quickly, `Extend` provides a way to eliminate the need for repeatedly calling `@property`

```py
>>> @Extend(pd.DataFrame, as_property=True)
... class _:
...     def nrows(self):
...         return self.shape[0]
...     def ncols(self):
...         return self.shape[1]
...
>>> df.nrows, df.ncols
(0, 0)
```

import inspect
from typing import (
    Callable,
    Optional,
    Iterable,
    Any,
    cast
)

"""
KEY TERMS (in context of this module)
-------------------------------------
extend:
    Normally, to "extend" a class is to create a child class with additional
    functionality. However, the purpose of this module is to make that happen
    inplace by setting attributes directly on targets. So "extend" really
    means "extend inplace", in this module.
target:
    Class which we're trying to extend by setting attributes directly
push:
    The act of setting a class attribute. Synonymous with ``setattr()``

"""

_history = set()


class ExistingAttributeError(Exception):
    """
    Friendly error to prevent accidental replacement of existing attributes.
    """
    pass


class _ExtendMeta(type):
    """
    First, for those who are skeptical, this metaclass exists to provide functionality
    that couldn't be implemented by object class ``__init_subclass__`` methods.
    It allows for immediate self-destruction of the placeholder classes that the
    end-user creates to hold attributes to push. (After defining a placeholder class,
    find it in globals() and notice that its value is None). This metaclass's
    functionality is only needed when defining a push group by subclassing ``Extend``

    Note about metaclasses: instances of this class are other classes, not objects.
    So, ``__new__`` is called upon creation of any class who declared this
    class as its metaclass.

    Notes about __new__()
    ---------------------
    Behaves normally when called from a class who directly declares
    this as its metaclass. However, when called from an instance's child,
    the calling class's arguments and attributes will be passed to a
    function that processes the extension, and the newly declared child
    class will be destroyed. And, the ``bases`` argument will be processed
    such that only its first element will be treated as normal, and the
    remaining classes specified will be treated as extension targets.

    For instance, if this code is passed ...
    >>> import pandas as pd
    >>> class _(Extend, pd.DataFrame, pd.Series):
    ...     ...

    Instead of trying to inherit from ``pd.DataFrame`` and ``pd.Series``,
    it will be interpreted as ...
    >>> class _(Extend, to = [pd.DataFrame, pd.Series]):
    ...     ...

    When evaluating the first example, we decide that since the first argument
    is an instance of ``_ExtendMeta``, all other types provided should be
    interpreted as targets
    """
    def __new__(
        cls,
        cls_name,
        bases,
        cls_dict,
        *,
        to: Iterable[type] | type | None = None,
        keep: bool = False,
        **kwargs,
    ) -> type:
        """
        Triggers extension and returns None when first element in `bases` is
        a child of an instance of `_ExtendMeta`. Otherwise acts normal.
        """
        if len(bases) > 0:
            if not isinstance(bases[0], _ExtendMeta):
                raise ValueError("First parent argument must be an instance of '_ExtendMeta'")
            if to is None:
                if len(bases) > 1:
                    bases, to = (bases[0],), bases[1:]
                else:
                    raise ValueError("missing param, 'to'")

            if not isinstance(to, Iterable):
                to = (to,)

            _push_cls_attrs(cls_dict=cls_dict, to=to, **kwargs)  # type: ignore

            if keep is False:
                return cast(_ExtendMeta, None)

        return super().__new__(cls, cls_name, bases, cls_dict)


class Extend(metaclass=_ExtendMeta):
    """
    Never directly instantiate this class. Either create a subclass, or use it
    as a decorator.
    When a subclass is created, ``_ExtendMeta`` will handle extension and this
    class will never be instantiated because ``_ExtendMeta``'s ``__new__`` will
    return ``None``. When used as a decorator over an element, this class's
    ``__new__`` will handle extension.

    Examples
    --------

    >>> import pandas as pd
    >>> df = pd.DataFrame({'a': [1,2], 'b': [3,4]})

    Push a single function to targets, ``pd.DataFrame`` and ``pd.Series``

    >>> @Extend(pd.DataFrame, pd.Series)
    ... def say_hi(self):
    ...     return 'hi'
    ...
    >>> df.say_hi() # can also be called from a Series
    'hi'

    Push the contents of a class to target, ``pd.DataFrame``

    >>> @Extend(pd.DataFrame)
    ... class _:
    ...     SOME_CONSTANT = 5
    ...     @property
    ...     def say_hello(self):
    ...         return 'hello'
    ...
    >>> df.say_hello
    'hello'
    >>> pd.DataFrame.SOME_CONSTANT
    5

    Or, subclass ``Extend`` for a more concise way to push a group of attributes.
    Push the contents of class ``_`` to targets, ``pd.DataFrame`` and ``pd.Series``

    >>> class _(Extend, pd.DataFrame, pd.Series):
    ...     ...

    The above code is made possible by ``_ExtendMeta``, whose ``__new__`` method
    will interpret all types listed after ``Extend`` as targets, not parents. The
    above code will be evaluated as ...

    >>> class _(Extend, to = [pd.DataFrame, pd.Series]):
    ...     ...

    Notes about __new__()
    ---------------------
    Called when decorating an element with `Extend` instead of subclassing it.
    Pass arguments to `Extend()`.

    1.  If decorating a function, the function will be pushed to the targets
    2.  If decorating a property directly, the ``@property`` syntax must be
        used (not ``property()``), and the ``@property`` decorator must be
        placed below ``@Extend()``
    3.  If decorating a class, all custom attributes of the class will be pushed,
        and, by default, deleted from the decorated class. This can be disabled
        with ``keep=False``

    `overwrite=True` allows replacement of attributes that already exist in target class
    and weren't already defined by the user.

    `keep=True` lets the decorated element remain in global scope

    `as_property=True` - All attributes will be converted to ``property`` type before
    being pushed. (Note: a ``@property`` decorator will still be required for any elements
    that are followed by corresponding ``@<func>.setter`` or ``@<func>.deleter`` methods.

    """

    def __new__(  # type: ignore
        cls,
        *args: type | Iterable[type],
        overwrite: bool = False,
        as_property: bool = False,
        keep: bool = False,
    ) -> Optional[Callable[..., Any]]:
        """
        Called when decorating an element with ``Extend``. Returns a wrapper function.
        """

        if len(args) == 0:
            raise ValueError("Must pass target class(es) as arguments")

        def inner(e: Callable[[Any], Any]):
            if inspect.isclass(e):
                _push_cls_attrs(
                    cls_dict=dict(e.__dict__),
                    to=args,
                    overwrite=overwrite,
                    as_property=as_property
                )

            elif inspect.isfunction(e) or isinstance(e, (property, classmethod, staticmethod)):
                if isinstance(e, property):
                    attr_name = getattr(e.fget, '__name__')
                else:
                    attr_name = getattr(e, '__name__')

                for target in _fmt_validate_target_args(args):
                    _push_attr(
                        target_cls=target,
                        attr_name=attr_name,
                        attr_obj=e,
                        overwrite=overwrite,
                        as_property=as_property,
                    )
            else:
                raise ValueError("Don't know how to handle this")  # Should come up missing in cov

            if keep is True:
                return e

        return inner


def _push_cls_attrs(
    cls_dict: dict[str, Any],
    to: tuple[type | Iterable[type], ...],
    overwrite: bool = False,
    as_property: bool = False,
) -> None:
    """
    Sets user-defined attributes in ``cls_dict`` as attributes of each target in ``to``
    """

    exclude_attrs = [
        "__weakref__",
        "__dict__",
        "__module__",
        "__doc__",
        "__qualname__"
     ]

    for attr_name, attr_obj in cls_dict.items():
        if attr_name in exclude_attrs:
            continue
        for target_cls in _fmt_validate_target_args(to):
            _push_attr(
                target_cls=target_cls,
                attr_name=attr_name,
                attr_obj=attr_obj,
                overwrite=overwrite,
                as_property=as_property,
            )


def _push_attr(
    target_cls: type,
    attr_name: str,
    attr_obj: Callable[[Any], Any] | property,
    overwrite: bool,
    as_property: bool,
) -> None:
    """
    Validate and push attribute, and record history.

    Raise
    -----
    TypeError:
        When ``as_property=True`` but ``attr`` is not a valid function
    ValueError:
        When ``as_property=True`` and ``attr`` takes invalid number of params (!= 1)
    ExistingAttributeError:
        When an attribute that isn't in ``_history`` is already exists on target, and ``overwrite=False``
    """
    if as_property is True and not isinstance(attr_obj, property):
        if not inspect.isfunction(attr_obj):
            raise TypeError(
                f"Can't convert '{attr_name}' from type '{type(attr_obj)}', to property"
            )
        if 1 != (num_params := len(inspect.getfullargspec(attr_obj).args)):
            raise ValueError(
                f"Function '{attr_name}' must require exactly 1 positional argument for it to "
                f"be converted to a property. It's defined to take {num_params}."
            )
        attr_obj = property(attr_obj)

    if overwrite is False:
        _validate_non_existing_attribute(target_cls=target_cls, attr_name=attr_name)

    _history.add(_make_history_key(target_cls, attr_name))
    setattr(target_cls, attr_name, attr_obj)


def _validate_non_existing_attribute(
    target_cls: type, attr_name: str,
) -> None:
    """
    Responsible for raising friendly ``ExistingAttributeError`` when target
    class already has a desired attribute that has not already added by the user

    Raise
    -----
    ExistingAttributeError:
        When an uncached attribute already exists on target, and ``overwrite = False``
    """
    if (
        hasattr(target_cls, attr_name) and
        (history_key := _make_history_key(target_cls, attr_name)) not in _history
    ):
        raise ExistingAttributeError(
            f"{'.'.join([k if k is not None else '<Unknown>' for k in history_key])} "
            "already exists. Pass `overwrite = True` to avoid this error."
        )


def _make_history_key(
    target_cls: type, attr_name: str
) -> tuple[str | None, str | None, str]:
    """
    Since ``_history`` persists globally, a robust unique identifier
    for each history record is needed: (module name, class name, attr name)

    Examples
    --------
    >>> import pandas as pd
    >>> _make_history_key(pd.DataFrame, "bar")
    ('pandas.core.frame', 'DataFrame', 'bar')

    """

    return (
        module.__name__ if (module := inspect.getmodule(target_cls)) is not None else None,
        target_cls.__name__ if hasattr(target_cls, '__name__') else None,
        attr_name
    )


def _fmt_validate_target_args(
    args: tuple[type | Iterable[type], ...],
) -> tuple[type, ...]:
    """
    Flatten and validate args of unknown format into a tuple of types
    """

    args = _flatten_iterable(args)

    if not all(isinstance(x, type) for x in args):
        raise TypeError("Targets must be of type, 'type'")
    else:
        return args  # type: ignore


def _flatten_iterable(
    args: Any
) -> tuple[Any, ...]:
    """
    Turns anything into a flattened tuple of non-iterable (str, bytes excluded) values

    >>> _flatten_iterable(int)
    (<class 'int'>,)

    >>> _flatten_iterable(['hi'])
    ('hi',)

    >>> _flatten_iterable(['hi', (1,3, [8]), [((3,3,3))]])
    ('hi', 1, 3, 8, 3, 3, 3)
    """

    def valid_iterable(e: Any) -> bool:
        if isinstance(e, Iterable) and not isinstance(e, (str, bytes)):
            return True
        return False

    def flatten(elems: Iterable[Any]):
        for e in elems:
            if valid_iterable(e):
                yield from flatten(e)
            else:
                yield e

    args = args if valid_iterable(args) else (args,)

    return tuple(flatten(args))


if __name__ == '__main__':
    import doctest
    doctest.testmod()


# def convert_to_extend_subclass(
#     from_cls: type, **kwargs
# ) -> Type[T]:
#     """
#     Alternative to calling ``cls.push_class_contents()`` directly.
#     Given a class and kwargs, this dynamically creates and returns a new
#     class that inherits from Extend, invoking its ``__init_subclass__()``,

#     Parameters
#     ----------
#     from_cls : type
#         Class containing attributes to be pushed.
#     kwargs
#         Keyword arguments to be passed as class-level keyword arguments to
#         the new class definition, to then be received by ``cls.__init_subclass__()``
#     """

#     updated_cls_dict = {
#             k:v for k,v in from_cls.__dict__.items()
#         if k not in ["__weakref__", "__dict__"]
#     }

#     return types.new_class(
#         from_cls.__name__,
#         bases=(Extend,),
#         kwds = kwargs,
#         exec_body = lambda body: (body.update(updated_cls_dict))
#     )

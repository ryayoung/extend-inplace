import inspect
import types
from typing import TypeVar, Type, Callable, Iterable

T = TypeVar('T', bound='Inject') # generic

_history = set()


class ExistingAttributeError(Exception):
    """
    Used to prevent accidental replacement of existing attributes.
    Raised when the user has chosen to prevent replacement (``overwrite = False``),
    and the attribute hasn't yet been recorded (which means it's not user-defined)
    """
    pass


def _inject_class_contents(
        cls_dict: dict,
        to: list | tuple | type,
        overwrite: bool = False,
        as_property: bool = False,
) -> None:
    """
    Sets each custom attribute of ``cls_dict`` as an attribute of the target
    class, for each target class in ``to``

    Parameters
    ----------
    cls_dict : type
        Class containing attributes to be injected.
    to : list or tuple or type
        Target class(es) for injection. Plural version of ``target_cls``. Flexible
        data type to accomodate a variety of callers. Gets converted to ``list``
    overwrite : bool, default False
        Allow replacement of attribute that already exists in target class
        and wasn't already defined by the user. Default is False to serve as a
        safeguard against *accidental* changes
    as_property : bool, default False
        When True, all attributes in ``cls_dict`` will be converted to ``property``
        type before injection. Therefore, all attributes *must* be of type ``function``
        or ``property``. This is useful when injecting a large quantity of
        functions, as a means of saving space by eliminating the need for repetitive
        ``@property`` decorators placed above each function. (Note: a ``@property``
        decorator will still be required for any elements that are followed by
        corresponding ``@<func>.setter`` or ``@<func>.deleter`` methods, as
        the python interpreter will try to evaluate them before the original
        getter function is converted to a property)
    """
    target_classes = _fmt_validate_target_args(to)

    filtered_cls_dict = {
            k:v for k,v in cls_dict.items()
        if k not in ["__weakref__", "__dict__", "__module__", "__doc__", "__qualname__"]
    }

    for attr_name, attr_obj in filtered_cls_dict.items():
        for target_cls in target_classes:
            _inject_attr_and_cache(
                target_cls=target_cls,
                attr_name=attr_name,
                attr_obj=attr_obj,
                overwrite=overwrite,
                as_property=as_property,
            )


class InjectMeta(type):
    """
    First, for those who are skeptical, this metaclass exists to provide functionality
    that couldn't be implemented by its instances' ``__init_subclass__`` methods.
    It allows for immediate self-destruction of placeholder classes containing
    attributes to inject, after injection. (After defining a placeholder class,
    find it in globals() and notice that its value is None)

    Note about metaclasses: instances of this class are other classes, not objects.
    So, ``__new__`` is called upon creation of any class who declared this
    class as its metaclass.
    """
    # @overload
    # def __new__(...):
        # ...
    def __new__(cls, cls_name, bases, cls_dict, *, # default args
        to: list|tuple|type|None = None,
        keep_cls: bool = False,
        **kwargs,
    ) -> type:
        """
        Behaves normally, unless called from the declaration of a class
        trying to inherit from an instance of this class. When this happens,
        the calling class's arguments and attributes will be passed to a
        function that processes the injection, and the newly declared child
        class will be destroyed. And, the ``bases`` argument will be processed
        such that only its first element will be treated as normal, and the
        remaining classes specified will be treated as injection targets.

        Note: This method is *first* called when creating a class that directly
        declares this class as its metaclass. During this first call, our global
        scope is limited to variables created before this class. We can identify
        the first call by checking that ``bases`` is empty. Once it's populated,
        we can safely access objects declared later.
        """

        if len(bases) > 0:
            if isinstance(bases[0], InjectMeta):
                if to is None:
                    if len(bases) > 1:
                        bases, to = (bases[0],), bases[1:]
                        print(to)
                    else:
                        raise ValueError("missing param, 'to'")

                _inject_class_contents(cls_dict=cls_dict, to=to, **kwargs)
                if keep_cls == False:
                    return

        return super().__new__(cls, cls_name, bases, cls_dict)


class Inject(metaclass=InjectMeta):
    """
    Subclassing ``Inject`` is the most concise way to inject a group of functions.
    It cannot be called directly - a child class must be created.
    A child will, upon instantiation, have all of its attributes injected into the
    target(s) specified in required arguments

    -   Class variable ``history`` lets notebook users enforce ``overwrite=False``
        without throwing errors upon repeated execution of cells. When False, an
        error is thrown if the target class already has an attribute with the same
        name as one that is to be injected, and the existing attribute has not already
        been injected. Keeping a historical record allows for previously added
        attributes to be ignored by the checks incurred by ``overwrite=False``

    Examples
    --------

    >>> import pandas as pd

    Subclassing ``Inject`` provides a more concise way to inject a group of attributes.
    For instance, the following code,

    >>> @inject(pd.DataFrame, pd.Series)
    ... class _:
    ...     ...

    Can also be expressed as,
    >>> class _(Inject, to = [pd.DataFrame, pd.Series]):
    ...     ...

    """

    def __new__(cls, *args, **kwargs):
        raise TypeError(f"Class cannot be instantiated")

    def __init_subclass__(
        cls, *, to: list|tuple|type, **kwargs
    ) -> None:
        """
        Child must pass class-level keyword arguments at instantiation.
        When a child is instantiated, pass the child class and keyword arguments
        to ``_inject_class_contents`` for injection.
        """
        _inject_class_contents(from_cls=cls, to=to, **kwargs)

VAR = 5


def inject(
    *args: tuple[type, ...] | tuple[Iterable[type]],
    overwrite: bool = False,
    as_property: bool = False,
    keep_cls: bool = False,
) -> Callable:
    """
    Inject the decorated element (or the elements in a decorated class)
    into selected classes. Accepts either a function, property, or a class.

    If decorating a property directly, the ``@property`` syntax must be
    used (not ``property()``), and the ``@property`` decorator must be
    placed below ``@inject()``

    If decorating a class, all custom attributes of the class, (including
    class variables, property setter/deleters, etc.) will be injected,
    and, by default, deleted from the decorated class. This can be disabled
    with ``del_old_attrs = False``

    Parameters
    ----------
    args : tuple[type, ...] or tuple[list[type] | tuple[type, ...]]
        Target class(es) to inject the decorated element into
    overwrite : bool, default False
        Allow replacement of attribute that already exists in target class
        and wasn't already defined by the user. Default is False to serve as a
        safeguard against *accidental* changes
    as_property : bool, default False
        When True, attribute(s) will be converted to ``property`` type before
        injection. Passed attributes *must* be of type ``function`` or ``property``.
        This is useful when injecting a class containing a large quantity of
        functions, as a means of saving space by eliminating the need for repetitive
        ``@property`` decorators placed above each function. (Note: a ``@property``
        decorator will still be required for any elements that are followed by
        corresponding ``@<func>.setter`` or ``@<func>.deleter`` methods, as
        the python interpreter will try to evaluate them before the original
        getter function is converted to a property)

    Examples:
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({'a': [1,2], 'b': [3,4]})

    Inject a single function to multiple target classes

    >>> @inject(pd.DataFrame, pd.Series)
    >>> def say_hi(self):
    >>>     return 'hi'
    >>> df.say_hi() # can be called on Series too
    hi

    Inject the entire contents of a class

    >>> @inject(pd.DataFrame)
    >>> class _:
    >>>     SOME_CONSTANT = 5
    >>>     @property
    >>>     def say_hi(self):
    >>>         return 'hi'
    >>> df.say_hi
    hi
    >>> pd.DataFrame.SOME_CONSTANT
    5

    A more concise but less intuitive alternative to decorating a class with
    ``inject()`` is to define a class which inherits from ``Inject`` and pass
    all necessary arguments as class-level keyword arguments

    For instance, this code ...
    >>> @inject(pd.DataFrame)
    >>> class _: ...

    can also be written as ...
    >>> class _(Inject, to = pd.DataFrame): ...


    Notes
    -----
    Will NOT work for decorating property setter/deleters, or class variables
    directly. To inject such types, decorate a class which contains them

    """

    def inner(e):

        if inspect.isclass(e):
            _inject_class_contents(
                cls_dict=e.__dict__,
                to=args,
                overwrite=overwrite,
                as_property=as_property
            )
            if keep_cls == True:
                return e

        elif inspect.isfunction(e) or isinstance(e, property):
            target_classes = _fmt_validate_target_args(args)
            name = e.fget.__name__ if isinstance(e, property) else e.__name__
            for cls in target_classes:
                _inject_attr_and_cache(
                    target_cls=cls,
                    attr_name=name,
                    attr_obj=e,
                    overwrite=overwrite,
                    as_property=as_property,
                )
        else:
            raise ValueError("Don't know how to handle this")
    return inner






def _inject_attr_and_cache(
    target_cls: type,
    attr_name: str,
    attr_obj: any,
    overwrite: bool,
    as_property: bool,
) -> None:
    """
    Validate and process request to inject attribute, and record history.

    Parameters
    ----------
    target_cls : type
        Target class into which ``attr_obj`` will be injected
    attr_name : str
        Name that ``target_cls`` will store ``attr_obj`` under
    attr_obj : any
        Attribute to inject into ``target_cls``
    overwrite : bool, default False
        Allow replacement of attribute that already exists in target class
        and wasn't defined by the user. Default is False to serve as a
        safeguard against *accidental* changes
    as_property : bool, default False
        When True, ``attr_obj`` will be converted to ``property`` type before
        injection. When True, ``attr_obj`` *must* be of type ``function`` or ``property``.

    Notes
    -----
    If ``as_property = True``, an error will be raised if ``attr_obj`` is not
    a valid function that takes a single positional parameter.

    Raise
    -----
    TypeError:
        When ``as_property = True`` and ``attr_obj`` is not a valid function
    ValueError:
        When ``as_property = True`` and ``attr_obj`` takes invalid number of params (!= 1)
    ExistingAttributeError:
        When an uncached attribute already exists on target, and ``overwrite = False``
    """
    if as_property == True and not isinstance(attr_obj, property):
        if not inspect.isfunction(attr_obj):
            raise TypeError(
                f"Can't convert '{attr_name}', of type '{type(attr_obj)}', to a property"
            )
        if 1 != (num_params := len(inspect.getfullargspec(attr_obj).args)):
            raise ValueError(
                f"Function '{attr_name}' must require exactly 1 positional argument for it to "
                f"be converted to a property. It's defined to take {num_params}."
            )
        attr_obj = property(attr_obj)


    if overwrite == False:
        _validate_non_existing_attribute(target_cls=target_cls, attr_name=attr_name)

    _history.add(_make_history_key(target_cls, attr_name))
    setattr(target_cls, attr_name, attr_obj)



def _validate_non_existing_attribute(
    target_cls: type, attr_name: str,
) -> None:
    """
    Responsible for raising friendly ``ExistingAttributeError`` when target
    class already has a desired attribute not already added by the user

    Parameters
    ----------
    target_cls : type
        Target class into which the attribute will be injected
    attr_name : str
        Name that ``target_cls`` will store the new attribute under

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
) -> tuple:
    """
    Since ``Inspect.history`` persists globally, a robust unique identifier
    for each history record is necessary: (module name, class name, attr name)

    Examples
    --------
    >>> import pandas as pd
    >>> @inject(pd.DataFrame)
    >>> def foo(self):
    >>>     ...
    >>> Inject.history
    {('pandas.core.frame', 'DataFrame', 'foo')}

    Notes
    -----
    First element in key will be ``None`` if ``inspect.getmodule()`` returns None

    """

    return (
        module.__name__ if (module := inspect.getmodule(target_cls)) is not None else None,
        target_cls.__name__ if hasattr(target_cls, '__name__') else None,
        attr_name
    )


def _fmt_validate_target_args(
    args: tuple | list | type
) -> tuple[type, ...]:
    """
    Flatten and validate args of unknown format into a tuple of types
    """

    args = _flatten_iterable(args)

    if not all(isinstance(x, type) for x in args):
        raise TypeError("Targets must be of type, 'type'")

    return args


def _flatten_iterable(
    args: any
) -> tuple[any, ...]:
    """
    Turns anything into a flattened tuple of non-iterable (str, bytes excluded) values

    >>> _flatten_iterable(int)
    (<class 'int'>,)

    >>> _flatten_iterable(['hi'])
    ('hi',)

    >>> _flatten_iterable(['hi', (1,3, [8]), [((3,3,3))]])
    ('hi', 1, 3, 8, 3, 3, 3)
    """

    valid_iterable = lambda e: isinstance(e, Iterable) and not isinstance(e, (str,bytes))

    def flatten(elems: Iterable):
        for e in elems:
            if valid_iterable(e):
                yield from flatten(e)
            else:
                yield e

    args = args if valid_iterable(args) else (args,)

    return tuple(flatten(args))


def convert_to_inject_subclass(
    from_cls: type, **kwargs
) -> Type[T]:
    """
    Alternative to calling ``cls.inject_class_contents()`` directly.
    Given a class and kwargs, this dynamically creates and returns a new
    class that inherits from Inject, invoking its ``__init_subclass__()``,

    Parameters
    ----------
    from_cls : type
        Class containing attributes to be injected.
    kwargs
        Keyword arguments to be passed as class-level keyword arguments to
        the new class definition, to then be received by ``cls.__init_subclass__()``
    """

    updated_cls_dict = {
            k:v for k,v in from_cls.__dict__.items()
        if k not in ["__weakref__", "__dict__"]
    }

    return types.new_class(
        from_cls.__name__,
        bases=(Inject,),
        kwds = kwargs,
        exec_body = lambda body: (body.update(updated_cls_dict))
    )



if __name__ == '__main__':
    import doctest
    doctest.testmod()

"""
TODO:

Make inject() a class!!
"""

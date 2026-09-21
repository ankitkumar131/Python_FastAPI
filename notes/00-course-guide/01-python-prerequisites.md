# 01 — Python prerequisites: understand the language behind the API

[Course map](./) · [Next: the web](02-web-http-rest.md)

## What is Python doing in a backend?

Python executes instructions on the server. A browser does not directly call a Python function over the internet. Later, FastAPI will translate an HTTP request into a normal function call. That makes functions, arguments and return values our first building blocks.

## Values, variables and collections

A **value** is a piece of information. A **variable** is a name referring to a value. `name = "Notebook"` associates a name with text; `=` assigns, whereas `==` compares. `str` is text, `int` a whole number, `float` an approximate decimal, `bool` either `True` or `False`. `None` means absence, not the empty string and not zero.

A **list** is an ordered collection, such as `["pen", "book"]`. A **dictionary** maps keys to values, such as `{"name": "pen", "price": 20}`. Use lists for many products and dictionaries for labelled properties. A **tuple** is a fixed, ordered collection often used to return several values. A **set** stores unique values; later we use it for permissions.

Square brackets select an item: `products[0]` selects the first list member; `product["name"]` selects a dictionary value. A missing dictionary key raises `KeyError`; `product.get("name")` returns `None` when absent. Choose deliberately: hiding every missing required key can hide a programming error.

## Functions, annotations and flow control

A function is a reusable recipe. `def total(price: int, quantity: int = 1) -> int:` declares its name, inputs and output hint. A **parameter** is the named input in the definition; an **argument** is a value supplied at a call. `return` ends the call and hands back a value. `print` only writes to the terminal; it does not send an API response.

**Type hints** describe expected types. Python normally does not enforce them: an ordinary function annotated `int` can still receive a string. FastAPI will inspect these annotations and arrange validation. `list[str]` means a list of strings; `str | None` means text or absence. This union does not automatically give a default value.

`if` chooses a branch. `for` repeats for each item. Indentation (normally four spaces) defines blocks; it is syntax, not decoration. A colon starts a block. `raise` stops normal flow with an exception, an object representing a failure. `try`/`except` handles a chosen failure; `finally` runs cleanup whether the operation succeeded or failed.

## Example and syntax

Save the following complete program and run it with `python examples/python_basics.py`. `python` starts the interpreter; the filename tells it which source file to execute.

## Example

### File: `examples/python_basics.py`

```python
def total(price: int, quantity: int = 1) -> int:
    if price < 0 or quantity < 1:
        raise ValueError("Invalid price or quantity")
    return price * quantity

products = [{"name": "Notebook", "price": 120}, {"name": "Pen", "price": 20}]
for product in products:
    print(product["name"], total(product["price"], quantity=2))
try:
    total(-1)
except ValueError as error:
    print(str(error))
```

## Code Explanation

### Line 1

`def` creates a function. Two integers are expected; omitting `quantity` uses one. The arrow documents an integer result.

### Line 2

`or` means either invalid condition is enough to enter this branch; `<` means less than.

### Line 3

Raising a built-in value error prevents an invalid total from being returned.

### Line 4

Multiplication calculates the total; `return` gives it to the caller.

### Line 5

This blank line separates logical parts; Python does not execute it.

### Line 6

This list contains two dictionaries. Integer prices represent minor currency units throughout this course.

### Line 7

Assign each dictionary to `product` in turn and execute the indented block.

### Line 8

Look up the name and price, call `total` with a named argument, and print the result.

### Line 9

Start a block in which a known failure may occur.

### Line 10

The default quantity is one; the negative price triggers `ValueError`.

### Line 11

Catch only `ValueError`, binding its exception object to `error`.

### Line 12

Convert the error to readable text instead of terminating with a traceback.

## Test it and what happens internally

Expected output:

```
Notebook 240
Pen 40
Invalid price or quantity
```

Python creates the function without running its body. A call creates local parameter bindings, executes the body, then returns. On the last call, the exception skips the normal return and looks for a matching handler. This is the same basic control flow used when an API rejects an operation.

## Classes, objects, imports and decorators

A **class** describes a kind of object. An **instance** is one object created from it. `class Product(BaseModel):` later means “define Product using BaseModel's behaviour.” This is **inheritance**: the child receives capabilities from a parent. An **attribute**, such as `product.name`, is a named value on an object. A **method** is a function associated with an object, such as `product.model_dump()`.

An **import** makes code from another module available. A module is usually a `.py` file. A package groups modules in a directory; our multi-file project includes `__init__.py` files to make that intent explicit. `from fastapi import FastAPI` imports one public name, not the entire internet. A **library** is reusable code; a **framework** is reusable code that also calls your code according to its rules.

A **decorator** is a callable used with `@` above a definition. Python calls it with the function being defined. It may return a wrapper or register the function somewhere. FastAPI route decorators register functions; they do not run the endpoint once for every line below them. We will inspect an actual route in chapter 03.

`Annotated[int, metadata]` attaches extra information to a type hint. The type is still `int`; FastAPI reads the extra information for input rules or dependencies. It comes from `typing`, Python's standard typing module.

## Resources, contexts and generators

A **resource** is something that must be released, such as an open file or database connection. A **context manager** provides entry and exit actions. `with open("notes.txt", encoding="utf-8") as file:` opens a file, binds it to `file`, and closes it on leaving the block, even after an exception. Use `with` instead of relying on eventual memory cleanup.

A **generator function** contains `yield`. Unlike `return`, `yield` pauses the function while retaining its local state. A later resumption continues after it. FastAPI uses a single yield in resource dependencies: set up → lend resource → clean up. Do not confuse this with returning many HTTP responses.

`**mapping` expands dictionary entries into named arguments; `Product(**data)` is similar to `Product(name=data["name"], ...)`. `{**old, **changes}` builds a new dictionary with later keys overriding earlier ones. `[...]` containing `for` is a **list comprehension**, a compact transformation we use in CRUD lists. We explain async syntax separately before performing asynchronous work.

## Why these features exist / when to use them

Functions avoid repeated recipes. Classes keep related data and behaviour together. Imports prevent every program becoming one huge file. Exceptions separate failure paths from successful return values. Context managers make cleanup reliable. Type hints make contracts visible to humans and tools. Use each when it removes repetition or expresses a real boundary; do not create a class for every three-line calculation or swallow every exception simply to make the program continue.

## Real-world use case

A checkout needs totals, validation and failure handling. The basic program already contains that business rule without any web framework. Keeping such rules independent lets you reuse them in an endpoint, a scheduled job and a test.

## Common Mistakes

* `def users():` with no indented body is a syntax error. Add an implementation; `pass` is a legal temporary empty body but returns `None`.
* `return print(products)` returns `None`, not the products. Return the data itself.
* `items=[]` as a normal function default is shared across calls. Use `None` and allocate a new list inside.
* Naming your module `fastapi.py`, `typing.py` or `json.py` can hide the library you intended to import.
* Catching `Exception` and returning `"ok"` hides real failures. Catch a specific error and decide how to recover.

## Best Practices

Use descriptive names, four spaces, small functions and explicit return values. Represent money as integer minor units or an explicitly chosen decimal type, not binary floats. Learn to read the final line of a traceback (Python's error report), then the file and line that caused it.

## Practice

Create `examples/practice_total.py`. Write a function returning the total for three pens costing 20 each. Reject zero quantity. Call it once successfully and once unsuccessfully, printing a friendly failure.

## Expected Result

```
60
Quantity must be positive
```

## Solution

### File: `examples/practice_total.py`

```python
def pen_total(quantity: int) -> int:
    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    return 20 * quantity

print(pen_total(3))
try:
    pen_total(0)
except ValueError as error:
    print(error)
```

Line 1 defines the input/output contract. Lines 2–3 guard invalid values. Line 4 calculates the valid result. Line 5 is spacing. Line 6 calls and prints. Line 7 starts error handling, line 8 triggers it, line 9 catches only the expected error, and line 10 prints its message. Run `python examples/practice_total.py` after saving the file.

## Summary

An API handler is still a Python function. The framework will choose its arguments and convert its return value, but the Python rules you learned here remain unchanged.

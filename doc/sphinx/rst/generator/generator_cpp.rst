.. _generator_cpp:

C++ code generator
==================

A complete C++ class can be generated with methods to read/write the registers or fields.

* :class:`.CppInterfaceGenerator` creates an abstract interface header that can be used for mocking
  in a unit test environment.
  Contains method declarations, register attributes, and register constant values.
* :class:`.CppHeaderGenerator` creates a class header which inherits the abstract class.
* :class:`.CppImplementationGenerator` creates a class implementation with setters and getters.

C++ code is generated by running the Python code below.
Note that it will parse and generate artifacts from the TOML file used in the :ref:`toml_formatting`
example.

.. literalinclude:: py/generator_cpp.py
   :caption: Python code that parses the example TOML file and generates the C++ code we need.
   :language: Python
   :linenos:
   :lines: 10-


Getters
-------

It can be noted, most clearly in the :ref:`interface_header` below, that there are three ways to
read a register field:

1. The method that reads the whole register, e.g. ``get_configuration()``.

2. The method that reads the register and then slices out the field value,
   e.g. ``get_configuration_enable()``.

3. The method that slices out the field value given a previously read register value,
   e.g. ``get_configuration_enable_from_value(register_value)``.

Method (2) is the most convenient in most cases.
However if we want to read out more than one field from a register it would be very inefficient to
read the register value more than once over the register bus, which would be the result of calling
(2) multiple times.
Instead we can call (1) once and then (3) multiple times to get our field values.


Setters
-------

Conversely there are three ways to write a register field:

1. The method that writes the whole register, e.g. ``set_configuration()``.

2. The method that reads the register, updates the value of the field, and then writes the register
   back, e.g. ``set_configuration_enable()``.

3. The method that updates the value of the field given a previously read register value,
   and returns an updated register value,
   e.g. ``set_configuration_enable_from_value(register_value)``.

Method (2) is the most convenient in most cases.
However if we want to update more than one field of a register it would be very inefficient to
read and write the register more than once over the register bus, which would be the result of
calling (2) multiple times.
Instead we can call a register getter once, e.g. ``get_configuration()``, and then (3) multiple
times to get our updated register value.
This value is then written over the register bus using (1).

Exceptions
__________

The discussion about setters above is valid for "read write" mode registers, which is arguably the
most common type.
However there are three register modes where the previously written register value can not be
read back over the bus and then modified: "write only", "write pulse", and "read, write pulse".
The field setters for registers of this mode will write all bits outside of the current field
as zero.
This can for example be seen in the setter ``set_channels_configuration_enable()`` in the generated
code :ref:`below <cpp_implementation>`.


.. _cpp_assertion_macros:

Assertion macros
----------------

There are a few register-related things that can go wrong in an embedded system:

1. An error in hardware might result in reading a field value that is out of bounds.
   This is mostly possible for :ref:`enumeration <field_enumeration>` and
   :ref:`integer <field_integer>` fields.

2. Conversely, an error in software might result in writing a field value that is out of bounds.

3. An error in software might result in a :ref:`register array <basic_feature_register_array>`
   read/write with an index that is out of bounds.

The generated C++ implementation checks for these errors using custom assertion macros.
Meaning, they can be detected at runtime as well as in unit tests.

If an assertion fails a user-specified handler function is called.
In this function, the user could e.g. call a custom logger, perform a controlled shutdown,
throw exceptions, etc.
One argument is provided that contains a descriptive error message.
The function must return a boolean ``true``.

This error handler function must be provided to the constructor of the generated class.


Minimal example
_______________

A minimal and somewhat unrealistic handler function is shown below.
More advanced handler functions are left to the user.

.. code-block:: C++

  uintptr_t base_address = 0x43C00000;

  bool register_assert_fail_handler(const std::string *diagnostic_message)
  {
    std::cerr << *diagnostic_message << std::endl;
    std::exit(EXIT_FAILURE);
    return true;
  }

  fpga_regs::Example example(base_address, register_assert_fail_handler);


Disabling assertions
____________________

The assertions add to the binary size and to the runtime of the program.
The user can disable the assertions by defining the following macros
(usually with the ``-D`` compiler flag):

1. ``NO_REGISTER_GETTER_ASSERT``

2. ``NO_REGISTER_SETTER_ASSERT``

3. ``NO_REGISTER_ARRAY_INDEX_ASSERT``

This should result in no overhead.


.. _interface_header:

Interface header
----------------

Below is the resulting abstract interface header code, generated from the
:ref:`toml_formatting` example.
Note that all register constants as well as field attributes are included here.

.. literalinclude:: ../../../../generated/sphinx_rst/register_code/generator/generator_cpp/include/i_example.h
  :caption: Example interface header
  :language: C++
  :linenos:


Class header
------------

Below is the generated class header:

.. literalinclude:: ../../../../generated/sphinx_rst/register_code/generator/generator_cpp/include/example.h
  :caption: Example class header
  :language: C++
  :linenos:



.. _cpp_implementation:

Implementation
--------------

Below is the generated class implementation:

.. literalinclude:: ../../../../generated/sphinx_rst/register_code/generator/generator_cpp/example.cpp
  :caption: Example class implementation
  :language: C++
  :linenos:

Note that when the register is part of an array, the register setter/getter takes a second
argument ``array_index``.
There is an assert that the user-provided array index is within the bounds of the array.

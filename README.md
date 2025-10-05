# asm67
HP woodstock assembler (For HP67/97 vintage calculator firmware)

## Description

This tool is used to assemble firmware code for the vintage calculators HP67
and HP97 form the late 1970s.

The original code (ass97.py, v1.7.3, 2011) was written by Oliver De Smet, and can be
found [here](https://www.hpcalc.org/details/9548).

The code is ported to python3 (3.11) and enhanced and modified.


## Features

- Supports different dialects, eg. both **delayed select rom 12** and **del sel rom C** as well as **nop** and **no operation** are supported.
- Automatically inserts **delayed select ROM x** before a **go to** or **jsb** instructions if needed
- Defines a useful extension: **delayed select rom auto** used to let the assembler insert the correct destination ROM of a **go to** or **jsb**
- Checks for dangerous **go to**'s at the last word of a ROM
- Implements a **public** keyword. See description below
- Implements simple conditional directives. See description below
- Outputs the assembled firmware in 3 different formats


## Usage

```
python3 asm67.py [-h] [--log] [--fwout {b,r,h}] [--pub] [--mirror] input

positional arguments:
  input            Input file (.asm can be omitted)

options:
  -h, --help       show this help message and exit
  --log            Output listing during assembly
  --fwout {b,r,h}  Firmware output file type (b: binary bank files, r: x11-calc rom, h: C-header)
  --pub            Output public file during assembly
  --mirror         Mirror bank1 1000-13ff and 1800-1fff from bank0
```


## Output

### Output files

- A list file (.lst) is always generated
- An optional public file (.pub) is generated when the --pub switch is used
- Firmware output is generated using the --fwout switch, see below


### Firmware output

The resulting output can be formatted in 3 ways:

#### 1. Binary

Two binary bank files with the extension **.bin** are produced.
One for bank0 and one for bank1.
Both are 8k bytes in size.


#### 2. Rom

A ROM file can be used to run the firmware in the x11-calc-67
simulator which can be found [here](https://github.com/mike632t/x11-calc)

The format is text based and consists of address:data pairs (octal).
Example:
```
00000:00000
00001:01747
00002:00264
00003:00247
00004:01074
00005:00330
...
```

#### 3. C-header

The C-header file format can be useful if the firmware needs to be included
in some project. The format is (note numbers in octal):
```
int fw_rom[] = {
  00000, 01747, 00264, 00247, 01074, 00330, 01160, 01570,
  01020, 00256, 01160, 00070, 00232, 00520, 00520, 01152,
  00067, 01020, 00564, 01245, 01550, 01020, 00610, 00464,
  00035, 00372, 00262, 00232, 00417, 00104, 00021, 01356,
  00043, 01334, 00044, 00111, 01514, 01473, 00224, 00061,
  00124, 00103, 00204, 01414, 00021, 01556, 00060, 00111,
  00223, 00214, 00111, 01104, 00420, 01500, 01300, 01414,
  ...
};
```



## Assembly syntax

### Comments

Two types of comments can be used
```
// this is a comment
# this is also a comment
        nop       // and this is a comment
```

### Labels

A label must start with a letter, and must be terminated by a colon
```
Label_1:   jsb Label_2

Label_2:   return
```


## Directives

### Special directives

- org _address_     Set the location counter to _address_
- bank _bank#_      Set the current bank to 0 or 1
- public _symbol_   Define a public symbol, exported in the **.pub** file

Example:
```
        bank 1
        org 0x520
        public Foo
Foo:    nop
        go to Foo
```

Will produce the following line in the public file:
```
#define Foo 0x1520
```


### Conditional assembly directives

The assembler implements the following directives:
- #if _expression_
- #elif _expression_
- #else
- #endif
- #define _symbol_ [_value_]
- #ifdef _symbol_
- #ifndef _symbol_
- #error _string_

The following expressions are allowed:
- Binary: x
- Equal: x == y
- Not equal: x != y
- Greater than: x > y
- Less than: x < y
- Less or equal: x <= y
- Logical and: x && y
- Logical or: x || y

Limitations:
- x and y above can only be a number or a defined symbol, not a new expression
- Parentheses are not allowed

Examples:
```
#define FOO 2
#if FOO < 2
    // this is skipped
#elif FOO > 2
#error FOO can not be greater than 2
#endif

#if 0
  // this is skipped
#elif 1
  // this in parsed
#endif

#ifndef FOO
  // this is skipped
#endif
```

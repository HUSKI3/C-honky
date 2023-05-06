> :warning: **C-Honky compiler is being rewritten**: This is due to numerous issues found with the old approach. We could no longer scale that code base. Currently the entire C-Honky -> ChonkyAssembly compiler is being rewritten  

![img](https://github.com/HUSKI3/C-honky/blob/main/img/Ch.png)
<h1 align="center">C-honky</h1>

<div align="center">
  🐈
</div>
<div align="center">
  <strong>A functional language for the ChonkPC CPU</strong>
</div>
<div align="center">
  C-honky pronounced "chonk-ee" is a programming language designed for the ChonkPC platform, it's able to create executable bytecode for generating a BIOS and soon programs to be loaded by the ChonkPC emulator.
</div>

<br />
<div align="center">
  <h3>
    <a href="">
      ChonkPC Reference (Private atm)
    </a>
    <span> | </span>
    <a href="https://github.com/HUSKI3/C-honky/wiki/Getting-started">
      Handbook
    </a>
  </h3>
</div>

<div align="center">
  <sub>Built with ❤︎ by
  <a href="https://github.com/liuk7071">Liuk707</a> and
  <a href="https://github.com/HUSKI3"> Artur (aka Huski3)</a>
</div>

## Table of Contents
- Features
- Example
- Philosophy
- Functions
- Libraries 

## Features
- __minimal size:__ generated binaries are optimized out of the box
- __function driven:__ c-honky is a functional language, making anything possible
- __little boilerplate:__ barely any boiler plate is required to start having fun with this language
- __minimal tooling:__ both compiler and assembler are bundled as one library
- __supports namespaces:__ namespaces are easy to set up and use
- __very cute:__ Named after Liuk's cat!

## Example
Hello world in C-honky:
```go
// test.ck
#mode "kernel";
#bitstart 10000000;
#bitend 10004000;
#bitdata 10002000;
// Include our standard library
#embed[ck] "std.ck"

std::println("Hello World!");
```
Want to see more examples? Check out the [Handbook](https://github.com/HUSKI3/C-honky/wiki/Getting-started).

## Philosophy
ChonkPC is a minimal 32bit CPU built from the ground up, therefore there is no compiler or assembler developed directly for it. C-honky provides a simplistic low level language to abstract >30k assembly lines of boilerplate code, it provides enough to be used for calculations, graphics, disk operations and more to come! 
The language syntax and semantics concept was first based on the toy language [Pyetty](https://github.com/HUSKI3/Pyetty), that was written entirely in Python. The syntax has been expanded to allow for lower level communication with the CPU and other components provided by the ChonkPC emulator.

## Functions
The entire language relies on the use of functions to decrease code redundancy and performance. Each functions address is stored in memory to be used later. 

Creating a function is as simple as providing the name and it's code block. *Currently no return statements are supported*
```go
// ...
func  HelloWorld(int  test1) void {
	if (test1  ==  1) {
		std::println("I'm one!");
	}
}
HelloWorld(1);
// Output: I'm one!
```

## Libraries
Currently C-honky has the following libraries:
- [std.ck](https://github.com/HUSKI3/C-honky/blob/main/libs/std.ck) - Standard library
- [gl.ck](https://github.com/HUSKI3/C-honky/blob/main/libs/gl.ck)  - Graphics library
- disk.ck - Abstracted Disk library
- dif.ck - Disk Interface

## Standard library
The standard library provides the ability to write to the console, ... and panic. Not much else is implemented there yet. The `print` and `println` functions have a limit of 100 characters.
```go
// Hello world with a panic!
#embed[ck] "std.ck"
std::print("Hello ");
std::println("world!");

if (1 != 0) {
	std::panic("[FATAL] Oh no! Math!");
}
```

## Graphics library
The graphics library works directly with the GPU by writing to different addresses to define properties of the triangles to be drawn, and then calls draw on them. You must clear the command fifo before writing again. 

Examples:
```go
// Gradient triangle example
#embed[ck] "gl.ck"

// Clear screen
GL::clear(0, 0, 0);

// Colours
int r =  50;
int g =  150;
int b =  200;

// Triangle
GL::tri( 120, 400,
	520, 400,
	320, 100,
	r, g, b,
	b, g, r,
	g, r, b
);

GL::draw_double();
```

## Disk and others are a WIP

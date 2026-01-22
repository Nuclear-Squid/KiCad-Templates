# KiCad-Templates

A Python program to help the conception of PCBs by importing predefined templates, containing standalone electronic functions.

## Why it matters

Some electronic functions may be very common, but hard or time-consuming to implement. For instance, integrating a microcontroller properly means making sure we have :

- good power management (with a strong voltage regulator and efficient bypass capacitors)
- a clean routing (to keep high-speed signals away from each other and maintain a good ground plane)
- a compact design
- easy to access GPIOs

![Example integration of an RP2040 MCU](documentation/mcu_example.png)

This project aims to aid engineers by easily reuse complex electronic functions to both speed up development, and ensure a high quality design.

## How it works

Each template is defined using KiCad’s “hierarchical sheet” system, which allows the whole template to be placed onto an existing schematic as a sort of dummy component, with all of it’s out-going connection being exported as standard pins, able to be reused in the larger sheet. This allows the engineer to write detailed documentation for each template, without it making the larger project messy.

More information on the schematic side of the project can be found in the `sch_api.md` file.

## Roadmap

For now, only the schematic imports are supported, as the PCB routing seemed to be more challenging : The files are more complex, we need to fix a couple issues detailed in `sch_api.md`, recreate the net list and update some information in the imported PCB files before integrating them into the board.

This is our main long-term objective, and we are actively working on the foundations needed for this feature.

Other (smaller) features we’d like to add are :

- a more straight forward way of creating a new project
- allow the user to define their own templates outside this application
- improve the user interface
- add a KiCad plugin interface, for a seamless integration

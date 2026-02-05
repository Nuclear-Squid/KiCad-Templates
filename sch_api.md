# Schematic API

## Structure

The original code, made by an LLM and provided by the client, allowed the placement and wiring of components using a Python script.

Two functions were added to the KicadSchematic class: one allowing the addition of hierarchical sheets to the working .sch file, and the other allowing the placement of multiple sheets at the same time.

The hierarchical functions take an object from the HierarchicalObject class, which, for the purpose of this project, will be one of the constant variables listed in the SCH_Templates class. This class is being filled with modular parts of the circuits provided by the client, which will later be used to generate the desired designs with a low time cost.

All hierarchical sheets are stored in the subsystems folder, as well as the temporary footprint library "exmplo".

## Current challenges

### The main project
The current version of the code is extremely reliant on the project in which it is set. For instance, it does not take any library address, since every hierarchical sheet has components whose descriptors reference the expected libraries locally by name. This means that, for the program dependencies to work, the user has to manually assign the components to a newly created footprint library for every new project.

Another implication of this problem is the need for the project to be a clean version of what is called by api.load_schematic(). If the file does not exist, the program stops working; if the file exists and already contains data, it may cause overlapping issues. Part of this problem can be partially solved with UX-oriented coding, but it seems inevitable that the user will have to follow specific steps, exposing the procedure to potential failure. With the code being as dependent as it is on the current project in which it is installed, there must be a schematic file named exactly like the project, and the editor window must be closed.

> **NOTE**: Both of these problems can be fixed with brute force by demanding the user to start every new project from a copy of one working version. This can be taken in consideration as a last resort.

### The next step
Apart from fixing the software inflexibility, considering that every footprint is correctly assigned, there are still lots of questions about how will it all connect to the pcb design half of the work. The current code is directly writing data into sch files, not taking any control on the Kicad, so the "anotate" option that transfers the schematic as a netlist is impossible without the users manual intervention. The only clear steps with the code as it is would be for the user to: create .shc-> run generator -> make the anotation -> run the second part of the code.

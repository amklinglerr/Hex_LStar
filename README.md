# L-Star Implementation in Hex World

## Summary
An implementation of Dana Angluin's L* Algorithm for exactly learning DFAs in polynomial time as explained in Chapter 8: "Learning Finite Automata by Experimentation" in "An Introduction to Computational Learning Theory" by Micheal J. Kearns and Umesh V. Vazirani. However, it has been slightly altered to fit with hex agents in the Hex World create by Professor Alfeld's 2024 SURF lab.
Interface with the program via `solver.py` and `run_tests.py`

When running `run_tests.py`, you can specify with the `accuracy` keyword if you want accuracy tests to be performed at every stage of looping through L-Star and editing M_Hat. This will print the accuracy reports to an Excel file called Acc_states_w_mem_per_eq.xls. <br/>
When running `solver.py`, you can also specify `accuracy`, but you can also use the `graphs` keyword to show if you want graphs to be drawn of the DFAs at every step as they are learned (this is not recommended, except if you are running a very small number of membership queries, or a very small grid in Hex World).

The implementation of L-Star specifically for HexWorld was created by Allison Klingler (@amklinglerr) and Skyler McDonnell (@s-a-mcdonnell) in Professor Scott Alfeld's Lab as part of the Amherst College Summer Undergraduate Research Fellowship (SURF) 2024. HexWorld itself, the physics simulator, was created together by all 5 members of Professor Alfeld's lab.

## File Contents
### Python files:<br/>
`direction_teacher.py` -> subclass of `teacher.py`, used for a DFA that represents which direction the agent turns in (if it does) <br/>
`hex_world` -> the Hex World physics simulator that the agent acts in <br/>
`learner.py` -> the Learner for the DFA <br/>
`make_alphabet.py` -> writes an alphabet into `alphabet.txt` based on constraints set in the python file (only needs to be run once per set of constraints)<br/>
`movement_teacher.py` -> subclass of `teacher.py`, used for a DFA that represents if an agent turns or not <br/>
`solver.py` -> solves for two DFAs based on the agent specified in find_next_move method in `hex_world.py` <br/>
`teacher.py` -> the Teacher for the DFA <br/>
`test_points.py` -> runs 10,000 tests to determine if the DFAs produced in `direction_dfa.txt` and `movement_dfa.txt` are accurate compared to the current agent <br/>

### Text files:
`alphabet.txt` -> text file containing alphabet for the DFAs to use, generated by `make_alphabet.py` <br/>
`direction_dfa.txt` -> one of two text files written to during `solver.pyv for one of the two DFAs produced there, corresponding to `direction_teacher.py` <br/>
`movement_dfa.txt` -> one of two text files written to during `solver.py` for one of the two DFAs produced there, corresponding to `movement_teacher.py` <br/>
`requirements.txt` -> the required python packages in a text file for ease of pip installation <br/>

## Python libraries required
matplotlib, networkx (but only if you want to graph the DFAs, which is not recommended for learning large agents) (see requirements.txt)

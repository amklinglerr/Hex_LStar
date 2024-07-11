import os
import sys
from learner import Learner
from movement_teacher import Movement_Teacher
from direction_teacher import Direction_Teacher
# import pdb; pdb.set_trace()

def __read_line(line):
    global alphabet
    # If the line ends in a new line character, add everything except the new line character as an entry in the alphabet
    if line[len(line) - 1] == "\n":
        assert len(line) == 4
        alphabet.append(line[0:len(line)-1])
    
    # If the line doesn't end in a new line character, add it as an entry in the alphabet
    else:
        assert len(line) == 3
        alphabet.append(line)

##########################################################################################################

alphabet = []

# reading the alphabet from a file
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
file = open(os.path.join(__location__, "alphabet.txt"), "r")
for line in file:
    __read_line(line)

# Create learners:
# 0 -> movement teacher, 1 -> direction teacher
movement_learner = Learner(alphabet=alphabet, teacher_type=0)
# TODO: Modify teachers to make algorithm work
# Learn movement teacher using L* (learners return learner DFA so we can use it as desired)
movement_DFA = movement_learner.lstar_algorithm()

breakpoint()

# Learn direction teacher using L*
direction_learner = Learner(alphabet=alphabet, teacher_type=1)
direction_DFA = direction_learner.lstar_algorithm()

# TODO: methods to predict the agent's reaction to certain states based on the two DFA's we've created
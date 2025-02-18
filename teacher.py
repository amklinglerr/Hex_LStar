import random
from hex_world import World, Ident
import make_alphabet
import pdb
import functools


def memoize(obj):
    '''memoize method and information from https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize'''
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]
    return memoizer

##############################################################################################################

class Teacher:

    ##########################################################################################################
    # NOTE: The maximum number of goals is arbitrary
    MAX_NUM_GOALS = 3
    
    # NOTE: The maximum number of idents is arbitrary
    MAX_NUM_IDENTS = 50

    # Constructor
    def __init__(self, alphabet, mem_per_eq:int=100, seed=-1, premade_dfa=None):
        '''
        Teacher constructor
        :param alphabet: the alphabet used for the Teacher's DFA M
        :param mem_per_eq: the number of membership queries per equivalence query in L-Star
        :param seed: seed for a randomly generated DFA, if applicable
        :param premade_dfa: a premade DFA, in the form of an array, to be the DFA M for the teacher, if applicable
        '''

        self.alphabet = alphabet

        self.mem_per_eq = mem_per_eq

        # Check the alphabet for validity (each symbol is three characters)
        for symbol in alphabet:
            if len(symbol) != 3:
                print("Error: Invalid alphabet. All symbols must be three hexadecimal characters.")
                exit(1)

        self.seed = seed
        if seed == -1:
            self.seed = 1821

        if premade_dfa:
            self.m = premade_dfa
        
        # Create empty world with space for idents
        self.world = World(display_window=False)

        # There is enough space for all regular idents and all goals in the ident list
        # NOTE: May need to add space here if allowing multiple agents to be created
        self.ident_list = []
        for i in range(Teacher.MAX_NUM_IDENTS + Teacher.MAX_NUM_GOALS):
            self.ident_list.append(Ident(matrix_index=-1, list_index=-1, world=self.world))
       
        self.agents = [Ident(matrix_index=-1, list_index=-1, world=self.world, property="agent")]*10
        
        self.goal_list = [Ident(matrix_index=-1, list_index=-1, world=self.world, property="goal")]*Teacher.MAX_NUM_GOALS
        
        # How many agents and idents are currently being used
        self.valid_idents = 0
        self.valid_agents = 0

        self.wall_list = []

        ''' walls just for the test case where things are a 5x5 square'''
        # NOTE: Remove these walls and expand the number of valid characters in the alphabet to enable worlds larger thatn 5x5
        for i in range(5, 12):
            new_ident = Ident(5, i, self.world)
            new_ident.state = -2
            self.world.hex_matrix[5][i].idents.append(new_ident)
            self.wall_list.append(new_ident)

            new_ident2 = Ident(11, i, self.world)
            new_ident2.state = -2
            self.world.hex_matrix[11][i].idents.append(new_ident2)
            self.wall_list.append(new_ident2)

            new_ident3 = Ident(i, 5, self.world)
            new_ident.state3 = -2
            self.world.hex_matrix[i][5].idents.append(new_ident3)
            self.wall_list.append(new_ident3)

            new_ident4 = Ident(i, 11, self.world)
            new_ident4.state = -2
            self.world.hex_matrix[i][11].idents.append(new_ident4)
            self.wall_list.append(new_ident4)
        

        self.surrounding_walls : int = len(self.wall_list)
        self.valid_walls : int = self.surrounding_walls

        # NOTE: This may need to be adjusted depending on the number of other (non-ring) walls allowed to be created
        for i in range (50):
            self.wall_list.append(Ident(matrix_index=-1, list_index=-1, world=self.world, state=-2))

    ##########################################################################################################

    def equivalent(self, m_hat):
        '''
        An equivalence query which determines if two DFAs, M and M_Hat, are equivalent.
        Returns either False if the DFAs are equivalent (to represent the lack of a countereaxmple).
        If the DFAs are not equivalent, return a counterexample string (a string that one DFA accepts and the other rejects)
        :param m_hat: the DFA being compared to Teacher's DFA (M)
        '''

        assert m_hat

        # Generate and test an arbitrarily large number of strings
        # for each of these strings, if self.member(s, self.m) is not self.member(s, m_hat), return s

        for i in range(self.mem_per_eq):
            s = Teacher.generate_string()
            # return counterexample if one exists
            if self.member(s) != self.member(s, m_hat):
                return s            

        # else return false (so that the truthiness of a counterexample and a matching DFA result will be different)
        print("No counterexample found")
        return False

    ##########################################################################################################
    
    @staticmethod
    def final_state(s : str, dfa: list[list[int]], alpha):
        '''
        Static method that returns the state in a specified DFA from a string (ie whether that string is rejected or accepted).
        :param s: the string we are checking
        :param dfa: the dfa we are putting the string through
        :param alpha: the alphabet that the string and the dfa share
        '''

        input = []

        assert (type(s) is str)

        # Convert passed string into an array of ints, where each int is the index in the alphabet array corresponding to that character
        for i in range(int(len(s)/3)):
            input.append(alpha.index(s[i*3 : i*3 + 3]))
        
        # Enter the DFA (M) at state 0
        next_state_index = 0

        # Navigate through the DFA to the final state
        for char_index in input:
            current_state = dfa[next_state_index]
            next_state_index = current_state[char_index + 1]
        
        # Return final state
        return dfa[next_state_index]
        
    ##########################################################################################################

    def _create_world(self, s):
        '''
        Creates an iteration of World from hexv2.py with the arrangement specified in s.
        Note that it does not create a completely new world, but sets certain idents to be "valid" as an effort for memory storage.
        :param s: The string that represents the world with 3 hexadecimal characters (ie. f66 is a goal ident in position 6, 6 on the hex grid)
        '''
    
        # Reset trackers how many idents are valid
        self.valid_idents = 0
        self.valid_agents = 0
        self.valid_goals = 0
        self.valid_walls = self.surrounding_walls

        # Assert that the length of the world-string is valid
        assert(len(s) % 3 == 0)

        for hex_row in self.world.hex_matrix:
            for hex in hex_row:
                hex.idents.clear()

        # Parse string into world
        for i in range(int((len(s))/3)):

            # splice the three character string into three one-character chunks
            property = int(s[i*3], 16)
            mi = int(s[i*3 + 1], 16)
            li = int(s[i*3 + 2], 16)
            
            
            # The first char in ever "letter" (3-char string) form the property
            # The properties are wall (0), stationary non-agent (1), moving agent (in directions 0 through 5, 1 through 7),
            # stationary agent (8), moving agent (in directions 0 through 5, 9 through e), and goal (f)

            # 0 => wall
            if property == 0:
                new_ident = self.wall_list[self.valid_walls]

                new_ident.matrix_index = mi
                new_ident.list_index = li
                assert new_ident.world == self.world

                new_ident.state = -2
                self.wall_list.insert(self.valid_walls, new_ident)
                self.valid_walls += 1

            # If not a wall, it goes on the ident list
            # (It already is on the ident list, but we iterate to indicate that it is valid)
            else:
                new_ident = self.ident_list[self.valid_idents]

                new_ident.matrix_index = mi
                new_ident.list_index = li
                assert new_ident.world == self.world
                self.valid_idents += 1
                self.world.hex_matrix[mi][li].idents.append(new_ident)


            # Set the new ident's state

            # 1 => stationary (non-agent)
            if property == 1:
                new_ident.state = -1
            
            # 2 => direction 0 (non-agent)
            # 3 => direction 1 (non-agent)
            # 4 => direction 2 (non-agent)
            # 5 => direction 3 (non-agent)
            # 6 => direction 4 (non-agent)
            # 7 => direction 5 (non-agent)
            elif property >= 2 and property <= 7:
                new_ident.state = property - 2
            
            # 8 => stationary (agent)
            if property == 8:
                new_ident.state = -1
                # new_world.agents.append(new_ident)
                self.valid_agents += 1
            
            # 9 => direction 0 (agent)
            # 10 => direction 1 (agent)
            # 11 => direction 2 (agent)
            # 12 => direction 3 (agent)
            # 13 => direction 4 (agent)
            # 14 => direction 5 (agent)
            elif property >= 9 and property <= 14:
                new_ident.state = property - 9
                # new_world.agents.append(new_ident)
                self.valid_agents += 1


            # 15 => goal (stationary)
            elif property == 15:
                new_ident.state = -1
                # Mark as goal
                new_ident.property = "goal"
                # new_world.goals.append(new_ident)
                self.goal_list.insert(self.valid_goals, new_ident)
                self.valid_goals += 1

            
            # Save the first ident described in the string as my_agent
            if i == 0:
                self.my_agent = new_ident

        
        # Set world to only contain valid idents by slicing lists stored in self
        self.world.ident_list = self.ident_list[0:self.valid_idents]
        self.world.agents = self.agents[0:self.valid_agents]
        self.world.wall_list = self.wall_list[0:self.valid_walls]
        self.world.goals = self.goal_list[0:self.valid_goals]
        assert self.my_agent.world == self.world

    ##########################################################################################################

    
    
    @memoize
    def member(self, s : str, dfa: list[list[int]] = None, alpha = None):
        '''
        Membership query
        :param s: a string to query
        :param dfa: a DFA represented as a 2D list
        returns a boolean indicating whether s is accepted or rejected by the given DFA
        '''

        if not dfa:
            dfa = self.m
        
        if not alpha:
            alpha = self.alphabet

        assert dfa

        # Return the int boolean indicating if the final state is an accept or reject state
        final_state : list[int] = Teacher.final_state(s, dfa, alpha)
        return bool(final_state[0])
    

    ##########################################################################################################

    @staticmethod
    # NOTE: This distance calculation overlaps with a method Allison wrote in World
    def __get_distance(id_1:list[int], id_2:list[int]):
        '''
        Calculates and returns the distance between two idents (in number of hexes)
        :param id_1:
        :param id_2:
        '''
        
        # The difference in the matrix index of the idents (vertical)
        mi_dist = id_1[1] - id_2[1]

        # The difference in the list index of the idents (northwest to southeast)
        li_dist = id_1[2] - id_2[2]

        # The total distance is greater of the absolute values of the two partial distances
        total_dist = abs(mi_dist)
        if abs(li_dist) > total_dist:
            total_dist = abs(li_dist)
        # If the partial distances are both positive or both negative, the total distance is the sum of their absolute values
        if ((mi_dist > 0) == (li_dist > 0)) and ((mi_dist < 0) == (li_dist < 0)):
            total_dist = abs(mi_dist) + abs(li_dist)
        
        return total_dist

    @staticmethod
    def __get_distance_and_direction(id:list[int], ag:list[int]):
        '''
        Calculates and returns the distance (in number of hexes) and angle between an agent and an ident
        Returns a list of two numbers, where the first is the distance (in terms of number of hexes) from agent to the given ident
        And the second is the relative direction from the agent in which one would have to travel to reach the ident
        :param id:
        :param ag:
        '''
        
        # The difference in the matrix index of the idents (vertical)
        mi_dist = id[1] - ag[1]

        # The difference in the list index of the idents (northwest to southeast)
        li_dist = id[2] - ag[2]
        
        # The direction in which the agent is currently pointing
        agent_dir = ag[0] - 9
        # If the agent is stationary, default to direction 0
        if agent_dir == -1:
            agent_dir = 0

        assert agent_dir >= 0
        assert agent_dir <= 5
        
        # The total distance is greater of the absolute values of the two partial distances
        total_dist = Teacher.__get_distance(id, ag)
        
        # Deal with ident in the same location as the agent
        if mi_dist == 0 and li_dist == 0:
            
            if id[0] >= 2 and id[0] <= 7:
                abs_angle = id[0] - 2
            elif id[0] >= 9 and id[0] <= 14:
                abs_angle = id[0] - 9
            else:
                assert (id[0] == 0 or id[0] == 1 or id[0] == 8 or id[0] == 15)
                return [total_dist, 0] 

        # Deal with ident on a straight northwest/southeast line
        elif li_dist == 0:
            assert mi_dist != 0

            abs_angle = 2 if mi_dist > 0 else 5
        
        # Deal with ident on a straight vertical line
        elif mi_dist == 0:
            assert li_dist != 0

            abs_angle = 3 if li_dist > 0 else 0
        
        # Deal with ident on a straight northeast/southwest line
        elif mi_dist == -li_dist:
            abs_angle = 1 if mi_dist > li_dist else 4
        
        # Deal with all other cases (not straight lines)
        else:
            # To find angle:
            # Find the hex on the same concentric ring which is one of the the 6 straight lines and is the closest to the desired ident but counter-clockwise from it
            if mi_dist > 0 and li_dist < 0:
                if abs(li_dist) > abs(mi_dist):
                    ref_angle = 0
                else:
                    assert abs(mi_dist) > abs(li_dist)
                    ref_angle = 1
            elif mi_dist > 0 and li_dist > 0:
                ref_angle = 2
            elif mi_dist < 0 and li_dist > 0:
                if abs(li_dist) > abs(mi_dist):
                    ref_angle = 3
                else:
                    assert abs(mi_dist) > abs(li_dist)
                    ref_angle = 4
            else:
                assert mi_dist < 0 and li_dist < 0
                ref_angle = 5

            # Get the distance from said reference hex to the desired ident. We can do this with a call to __get_distance_and_direction because it will be a straight line (not infinite recursion)
            match ref_angle:
                case 0:
                    offset = Teacher.__get_distance([ag[0], ag[1], ag[2] - total_dist], id)
                case 1:
                    offset = Teacher.__get_distance([ag[0], ag[1] + total_dist, ag[2] - total_dist], id)
                case 2:
                    offset = Teacher.__get_distance([ag[0], ag[1] + total_dist, ag[2]], id)
                case 3:
                    offset = Teacher.__get_distance([ag[0], ag[1], ag[2] + total_dist], id)
                case 4:
                    offset = Teacher.__get_distance([ag[0], ag[1] - total_dist, ag[2] + total_dist], id)
                case 5:
                    offset = Teacher.__get_distance([ag[0], ag[1] - total_dist, ag[2]], id)
                case _:
                    exit(f"invalid ref angle {ref_angle}")
            

            # The angle of the desired ident = the angle of the reference hex + (distance from reference hex to desired ident)/(side length of ring - 1)
            # = angle of reference hex + (distance from ref hex to desired ident)/(# of ring)
            # = angle of reference hex + (distance from ref hex to desired ident)/(total_dist)
            abs_angle = ref_angle + offset/total_dist

        # Calculate relative angle (relationship between absolute angle and the agent's direction)
        if abs(abs_angle - agent_dir) <= 3:
            relative_angle = abs_angle - agent_dir
        elif (abs_angle - agent_dir <= 0) and (abs_angle - agent_dir < -3):
            relative_angle =  (abs_angle - agent_dir)%6

        else:
            
            assert abs_angle - agent_dir > 0

            assert abs_angle - agent_dir > 3

            relative_angle = abs_angle - agent_dir - 6
        
        assert abs(relative_angle) <= 3

        return[total_dist, relative_angle]

    ##########################################################################################################

    @staticmethod
    def stationary_ident(ident):
        '''
        Returns a boolean indicating if the given ident represents a stationary ident or not
        :param ident: a list of three (decimal) numbers representing a three-char string representing an ident
        '''
        return ident[2] == 1 or ident[2] == 8 or ident[2] == 15

    ##########################################################################################################

    @staticmethod
    def less_than(ident_1 : str, ident_2 : str, agent : str):
        '''
        Returns a boolean indicating if ident_1 is strictly "less than" ident_2 according to the following rules:
        First, sort by distance from agent
        Second, sort by angle relative to agent's angle
        Finally, sort by the first hexadecimal character (property)
        :param ident_1: a string representing an ident
        :param ident_2: a string representing an ident
        :param agent: a string representing the agent from whose perspective the sorting is being done
        '''

        # Ensure that we are comparing two idents of valid string length
        assert len(ident_1) == 3
        assert len(ident_2) == 3

        # Sort by distance from agent, then clockwise starting at direction 0 (12 o'clock)
        assert agent
        assert len(agent) == 3
        
        
        id_1 = []
        for char in ident_1:
            # Append all chars in ident_2 as ints in base 10
            id_1.append(int(char, 16))
        
        id_2 = []
        for char in ident_2:
            # Append all chars in ident_2 as ints in base 10
            id_2.append(int(char, 16))
        
        ag = []
        for char in agent:
            ag.append(int(char, 16))
        
        # Assert that agent is an agent (first char between 9 and e, inclusive)
        assert ag[0] >= 9 and ag[0] <= 14

        distance_1 = Teacher.__get_distance_and_direction(id_1, ag)
        distance_2 = Teacher.__get_distance_and_direction(id_2, ag)

        if distance_1[0] != distance_2[0]:
            return distance_1[0] < distance_2[0]
        else:
            # Idents at the same distance from the agent where only one is stationary
            if (Teacher.stationary_ident(id_1)) != (Teacher.stationary_ident(id_2)):
                return Teacher.stationary_ident(id_1)
        
            # Idents at the same distance from the agent where one is more directly on its current path
            elif abs(distance_1[1]) != abs(distance_2[1]):
                return abs(distance_1[1]) < abs(distance_2[1])
            
            # Idents at the same distance from the agent where both are symmetrically at angles to the agent's direction of motion
            elif distance_1[1] == -distance_2[1]:
                return distance_1[1] < distance_2[1]
            
            # Two idents are in the same location
            else:
                # Compare 1st hexadecimal character (property)
                if ident_1[0] < ident_2[0]:
                    return True
                elif ident_1[0] > ident_2[0]:
                    return False
                else:
                    # Two identical idents (should not happen)
                    print(f"ident_1 = {ident_1}, ident_2 = {ident_2}, agent = {agent}")
                    print(f"dist_1 = {distance_1}, dist_2 = {distance_2}")
                    exit("Two equal idents found")

    ##########################################################################################################

    @staticmethod
    def generate_string():
        '''
        static method that generates a random string with specified parameters such that it is a world
        currently: generates a string of characters where each "character" is 3 hexadecimal figures
        the string begins with the agent we are focusing on as our current agent
        '''

        strg = ""

        # Generate a valid agent of random direction and location
        my_agent = ""
        while not make_alphabet.check_validity(my_agent):
            my_agent = ""
            agent_dir = random.randint(9, 14)
            agent_mi = random.randint(0, 15)
            agent_li = random.randint(0, 15)
            my_agent += hex(agent_dir)[2] + hex(agent_mi)[2] + hex(agent_li)[2]

        assert my_agent

        # Save valid agent
        strg += my_agent

        # Generate (a) valid goal(s) of random location
        num_goals = random.randint(1, Teacher.MAX_NUM_GOALS)
        goals = []
        for i in range(num_goals):
            my_goal = ""
            while not (make_alphabet.check_validity(my_goal) and my_goal not in goals):
                my_goal = ""
                goal_mi = random.randint(0, 15)
                goal_li = random.randint(0, 15)
                my_goal += "f" + hex(goal_mi)[2] + hex(goal_li)[2]

            assert my_goal

            # Save new ident in the correct order
            # If other_idents is empty, add to it
            if not len(goals):
                goals.append(my_goal)
            
            # Add the final ident in other_idents in smaller than the new_ident, add at the back
            elif Teacher.less_than(goals[len(goals) - 1], my_goal, my_agent):
                goals.append(my_goal)

            # Otherwise iterate through other_ident until the correct location is found
            else:
                for goal in goals:
                    if not Teacher.less_than(goal, my_goal, my_agent):
                        goals.insert(goals.index(goal), my_goal)
                        break


        # Append valid goals to string
        for goal in goals:
            strg += goal

        
        # the below is commented out for our current 5x5 experiment.
        # the below code generalizes the string further and allows for more complicated arrangements of hex world.
        '''
        # Generate a pseudo-randomly determined number of other 3-char strings (idents)
        # NOTE: The choice of maximum number of idents is arbitrary; We might want to set to 0 for testing
        other_idents = []
        for i in range(Teacher.MAX_NUM_IDENTS):
            # breakpoint()
            new_ident = ""
            
            # Loop until we have made a novel valid ident
            while not (make_alphabet.check_validity(new_ident) and new_ident not in other_idents):
                new_ident = ""
                # breakpoint()
                # NOTE: the new idents cannot be goals
                ident_prop = random.randint(0, 14)
                ident_mi = random.randint(0, 15)
                ident_li = random.randint(0, 15)
                new_ident += hex(ident_prop)[2] + hex(ident_mi)[2] + hex(ident_li)[2]

            assert new_ident
            assert new_ident not in other_idents

            # Save new ident in the correct order
            # If other_idents is empty, add to it
            if not len(other_idents):
                goals.append(new_ident)
            
            # Add the final ident in other_idents in smaller than the new_ident, add at the back
            elif Teacher.less_than(other_idents[len(other_idents) - 1], new_ident, my_agent):
                other_idents.append(new_ident)

            # Otherwise iterate through other_ident until the correct location is found
            else:
                for ident in other_idents:
                    if not Teacher.less_than(ident, new_ident, my_agent):
                        other_idents.insert(other_idents.index(ident), new_ident)
                        break
        '''
        
        return strg


    ##########################################################################################################

##############################################################################################################
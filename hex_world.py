import time
import copy
import os
import pygame

'''
Process of the game:
0. Iterate over Idents
1. a: If an ident is in a head on collision with another ident, it flips in place
   b: Else, move the ident forward into the next hex
2. Resolve collisions. For hexes that contain multiple idents...
   a: If it has an ident of opposite direction in that hex, bounce off/reverse direction
   b: Else, take the average of all other idents EXCEPT SELF, but break ties by using the opposite ident of self
3. Resolve idents moved into a different hex during step 2
'''

# for storing information about a particular moving hex
class Ident:

    # Static variable to track number of Idents created
    idents_created = 0

    ##########################################################################################################
    
    def __init__(self, matrix_index, list_index, world, color=(255, 255, 255), state: int = -1, serial_number = -1, hist = None, property = None):
        '''
        Ident constructor
        :param matrix_index: an int representing the index of the list in the world.hex_matrix in which the Ident is located
        :param list_index: an int representing the index of the Hex in world.hex_matrix[matrix_ident] in which the Ident is located
        :param world: the World in which the Ident is located
        :param color: the color of the Ident
        :param state: an int representing the state (wall, stationary, or direction) of the Ident
        :param serial_number: int serial number (to check against accidental cloning)
        :param hist: the history of the ident (for backstepping)
        :param property: a string representing the special property of the ident, if any (ex. "goal")
        '''


        if hist is None:
            hist = []
        self.color = color

        self.state : int = state

        self.hist = hist
        if serial_number == -1:
            # If no serial number is provided
            self.serial_number = Ident.idents_created

            '''print("Ident with serial number " + str(self.serial_number) + " created")
            if state == -2:
                print("Is a wall")
            elif state == -1:
                print("Is stationary")
            else:
                print("Is moving")'''
            Ident.idents_created += 1
        else:
            self.serial_number = serial_number

        self.matrix_index = matrix_index
        self.list_index = list_index

        self.world = world

        self.property = property

    ##########################################################################################################

    def get_neighbor(self, matrix, dir):
        '''Public version of __get_neighbor()'''
        return self.__get_neighbor(matrix, dir)

    ##########################################################################################################


    def __get_neighbor(self, matrix, dir):
        '''
        Returns the neighboring hex in the given direction in the given matrix.
        If that hex does not exist, returns None
        :param matrix: the hex matrix that includes the ident
        :param dir: an int representing the direction of interest
        '''
        
        if dir == 0:
            # print("neighbor 0")
            try:
                return matrix[self.matrix_index][self.list_index - 1]
            except:
                return None
            
        elif dir == 1:
            # print("neighbor 1")
            try:
                return matrix[self.matrix_index + 1][self.list_index - 1]  
            except:
                return None

        elif dir == 2:
            # print("neighbor 2")
            try:
                return matrix[self.matrix_index + 1][self.list_index]
            except:
                return None

        elif dir == 3:
            # print("neighbor 3")
            try:
                return matrix[self.matrix_index][self.list_index + 1]
            except:
                return None

        elif dir == 4:
            # print("neighbor 4")
            try:
                return matrix[self.matrix_index - 1][self.list_index + 1]
            except:
                return None
            
        elif dir == 5:
            # print("neighbor 5")
            try:
                return matrix[self.matrix_index - 1][self.list_index]
            except:
                return None
            
        else:
            print("Invalid direction " + str(dir) + " passed to Ident.__get_neighbor(dir)")
            return None
        
    ##########################################################################################################

    def remove_repeats(self, id_list):
        '''
        Finds the ident(s) with the same serial number as self in the passed list and removes them from list
        :param id_list: the list of Idents from which repeats should be removed
        '''
        for ident in id_list:
            if ident.serial_number == self.serial_number:
                id_list.remove(ident)


    ##########################################################################################################


    @staticmethod
    def __remove_pairs(hex, dir, directions):
        '''
        Helper method for resolve_collisions()
        Takes the hex in which the ident is located and the direcs list of other idents in that hex.
        Returns the direcs list with pairs of idents which cancel out removed
        :param dir: int, state of Ident from which method was called
        :param directions: list of Idents in the same Hex as Ident from which method was called
        '''
        direcs = directions.copy()


        if dir == -1:
        
            hex_zero = hex.contains_direction(0)
            hex_three = hex.contains_direction(3)
            if hex_zero and hex_three:
                direcs.remove(hex_zero)
                direcs.remove(hex_three)
            
            hex_one = hex.contains_direction(1)
            hex_four = hex.contains_direction(4)
            if hex_one and hex_four:
                direcs.remove(hex_one)
                direcs.remove(hex_four)

            hex_two = hex.contains_direction(2)
            hex_five = hex.contains_direction(5)
            if hex_two and hex_five:
                direcs.remove(hex_two)
                direcs.remove(hex_five)
            
            return direcs

        else:
            
            # NOTE: using contains_direction leaves us vulnerable if there are somehow multiple idents in the hex that share a direction

            hex_plus_one = hex.contains_direction((dir + 1) % 6)
            hex_minus_two = hex.contains_direction((dir - 2) % 6)
            if hex_plus_one and hex_minus_two:
                direcs.remove(hex_plus_one)
                direcs.remove(hex_minus_two)
            
            hex_plus_two = hex.contains_direction((dir + 2) % 6)
            hex_minus_one = hex.contains_direction((dir - 1) % 6)
            if hex_plus_two and hex_minus_one:
                direcs.remove(hex_plus_two)
                direcs.remove(hex_minus_one)
        
        return direcs

    ##########################################################################################################

    def find_offset(self, other):
        '''
        Returns the absolute value of the difference between the directions of two idents
        :param other: the Ident with which to compare self
        '''
        for i in range(5):
            if ((self.state + i) % 6 == other.state) or ((self.state - i) % 6 == other.state):
                return i

    ##########################################################################################################

    def is_goal(self):
        '''Returns a boolean indicating whether the given ident is a goalpost'''
        return self in self.world.goals
    
    ##########################################################################################################

    # note that I should never have to deal with walls in this method
    # note that this reads from hex_matrix_new and ident_list_new and writes to hex_matrix and ident_list
    def resolve_collisions(self):
        '''Resolves collisions for hexes containing multiple idents'''
        w = self.world
        hex = w.hex_matrix_new[self.matrix_index][self.list_index]

        if (hex.contains_property("agent")):
            maybe_goal = next((Ident for Ident in w.goals if (Ident.matrix_index == self.matrix_index) and (Ident.list_index == self.list_index)), None)
            # find the first ident in goals with matching grid positions to self
            # if it exists, close da game!!!
            if maybe_goal is not None:
                w.goalEnd = True
                return

        # The hex to which we will be writing
        write_to_hex = w.hex_matrix[self.matrix_index][self.list_index]

        # obtain the hex that this ident is currently a part of
        hex = w.hex_matrix_new[self.matrix_index][self.list_index]
        
        # If self is the only ident in the hex, copy self into the future
        if len(hex.idents) <= 1:
            # print("No collision to resolve")


            if (self.state != -1) or (len(write_to_hex.idents) == 0):
                self.rotate_adopt(write_to_hex, w.ident_list, dir_final = self.state)

            return
        
        # now we have determined that the ident has other idents with it

        dir = self.state

        # Store all idents in self's hex except for self
        directions = []
        for ident in hex.idents:
            if ident.serial_number != self.serial_number:
                directions.append(ident)

        
        if not hex.contains_stationary():
            # if we contain opposite pairs, remove them from the directions list
            directions = self.__remove_pairs(hex, dir, directions)
            
            # if we ended up with a net zero average (all other idents in the hex cancelled out in opposite pairs),
            # bounce off in the opposite direction from what is currently held
            if len(directions) == 0:
                self.rotate_adopt(write_to_hex, w.ident_list)

            # if, at this point, there is only one direction left, take that one
            elif len(directions) == 1:
                print("rotate call e")
                self.rotate_adopt(write_to_hex, w.ident_list, dir_final = directions[0].state)

            # otherwise, there are exactly two other directions stored in this hex
            else:
                # Sanity checks
                assert(len(directions) == 2)
                assert(directions[0].state != directions[1].state)
                assert(directions[0].state != self.state)
                assert(directions[1].state != self.state)

                # if the other two are at 120 degrees to each other, take the value in between
                if (directions[0].state + 2)%6 == directions[1].state:
                    print("rotate call a")
                    self.rotate_adopt(write_to_hex, w.ident_list, dir_final = (directions[0].state + 1)%6)
                elif (directions[0].state - 2)%6 == directions[1].state:
                    print("rotate call b")
                    self.rotate_adopt(write_to_hex, w.ident_list, dir_final = (directions[0].state - 1)%6)
                
                # if the other two cohabitants are adjacent to one another (60 degrees), take the state of the one we are further away from
                else:
                    assert(((directions[0].state + 1)%6 == directions[1].state) or ((directions[0].state - 1)%6 == directions[1].state))
                    
                    closer_to_dir_0 = (abs(self.state - directions[0].state)%6) < (abs(self.state - directions[1].state)%6)
                    
                    # if current direction is closer to directions[0] than directions[1], take the state of directions[1]
                    if closer_to_dir_0:
                        print("rotate call c")
                        self.rotate_adopt(write_to_hex, w.ident_list, dir_final = directions[1].state)
                    # else take the state of directions[0]
                    else:
                        print("rotate call d")
                        self.rotate_adopt(write_to_hex, w.ident_list, dir_final = directions[0].state)

        # else, we are dealing with multiple idents, including a stationary ident
        else:
            assert(hex.contains_direction(-1))
            
            # A stationary ident colliding with a moving ident
            if self.state == -1:

                # if we contain opposite pairs, remove them from the directions list
                directions = self.__remove_pairs(hex, dir, directions)

                # If there are no idents left in directions, remain stationary
                if len(directions) == 0:
                    my_copy = self.__copy()
                    write_to_hex.idents.append(my_copy)
                    w.ident_list.append(my_copy)

                    if self in w.agents:
                        w.swap_agents(self, my_copy)


                # If there is only one ident left in directions, take its state
                elif len(directions) == 1:
                    self.rotate_adopt(write_to_hex, w.ident_list, dir_final = directions[0].state)
            
                elif len(directions) == 2:
                        # if the other two are at 120 degrees to each other, take the value in between
                    if (directions[0].state + 2)%6 == directions[1].state:
                        print("rotate call a")
                        self.rotate_adopt(write_to_hex, w.ident_list, dir_final = (directions[0].state + 1)%6)
                    elif (directions[0].state - 2)%6 == directions[1].state:
                        print("rotate call b")
                        self.rotate_adopt(write_to_hex, w.ident_list, dir_final = (directions[0].state - 1)%6)
                    
                    # if the other two cohabitants are adjacent to one another (60 degrees), take one of the states (arbitrary formula)
                    # NOTE: ^^ This is an arbitrary decision ^^
                    else:
                        assert(directions[0].state != -1 and directions[1].state != -1)

                        assert(((directions[0].state + 1)%6 == directions[1].state) or ((directions[0].state - 1)%6 == directions[1].state))
                        
                        state_to_take = directions[0].state
                        if (directions[0].state - directions[1].state)%6 > 2:
                            state_to_take = directions[1].state
                        
                        self.rotate_adopt(write_to_hex, w.ident_list, dir_final = state_to_take)
                        
                        
                elif len(directions) == 3:
                    # If there are three moving idents which have not been removed from directions,
                    # they are either all adjacent to one another
                    # or they are symmetrical (all at 120 degrees from one another)
                    
                    # Symmetrical case --> stationary hex does not move
                    if (directions[0].find_offset(directions[1]) == 2 and directions[1].find_offset(directions[2]) == 2):
                        my_copy = self.__copy()
                        write_to_hex.idents.append(my_copy)
                        w.ident_list.append(my_copy)

                        if self in w.agents:
                            w.swap_agents(self, my_copy)
                    
                    # Adjacent case (the three moving idents are clumped together) --> stationary hex is bumped in the direction of the middle ident
                    else:
                        
                        direc_0_1_offset = directions[0].find_offset(directions[1])
                        direc_1_2_offset = directions[1].find_offset(directions[2])
                        direc_0_2_offset = directions[0].find_offset(directions[2])
                        
                        # If directions[0] has the middle state, take that state
                        if direc_0_1_offset == 1 and direc_0_2_offset == 1:
                            self.rotate_adopt(write_to_hex, w.ident_list, dir_final = directions[0].state)
                        
                        # If directions[1] has the middle state, take that state
                        elif direc_1_2_offset == 1 and direc_0_1_offset == 1:
                            self.rotate_adopt(write_to_hex, w.ident_list, dir_final = directions[1].state)

                        # If directions[2] has the middle state, take that state
                        elif direc_0_2_offset == 1 and direc_1_2_offset == 1:
                            self.rotate_adopt(write_to_hex, w.ident_list, dir_final = directions[2].state)

                        else:
                            # None of the three idents have been calcualted to be in the middle
                            print("Error: No middle direction found")
                            pass

                else:
                    print("Error: Unexpected length of directions")
                    pass

            # A moving ident colliding with a stationary ident
            else:

                assert self.state >= 0

                hex_of_origin = self.__get_neighbor(w.hex_matrix, (self.state + 3)%6)
                assert hex_of_origin

                # If an ident with the opposite state is present, bounce off
                if hex.contains_direction((dir + 3) % 6):
                    modified_copy = self.rotate_adopt(hex_of_origin, w.ident_list)

                    # Save hex and ident to double-check for superimposed idents
                    w.double_check.append([hex_of_origin, modified_copy])

                
                # If two idents that sum to the opposite state are present, bounce off
                elif hex.contains_direction((dir + 2) % 6) and hex.contains_direction((dir + 4) % 6):
                    modified_copy = self.rotate_adopt([hex_of_origin, w.ident_list])
                    
                    # Save hex and ident to double-check for superimposed idents
                    w.double_check.append([hex_of_origin, modified_copy])


                # Else become stationary
                else:


                    print("ident with serial number " + str(self.serial_number) + " becoming stationary")
                    modified_copy = self.rotate_adopt(hex_of_origin, w.ident_list, dir_final = - 1)
                    
                    # Save hex and ident to double-check for superimposed idents
                    w.double_check.append([hex_of_origin, modified_copy])

                    # additionally, check the two immediate neighbors of the stationary hex to see if it has stationary neighbors, and if so, those start moving too
                    left_neighbor = self.__get_neighbor(w.hex_matrix_new, (self.state - 2)%6)
                    right_neighbor = self.__get_neighbor(w.hex_matrix_new, (self.state + 2)%6)
                    # NOTE: you only influence a neighbor if that neighbor is not being influenced by its own direct hit
                    if left_neighbor is not None:
                        ident_to_edit = left_neighbor.contains_direction(-1)
                        if (ident_to_edit is not None) and (len(left_neighbor.idents) == 1):
                            # if the left neighbor of the original stationary wall is also stationary, make it move
                            print("Influencing left stationary neighbor")
                            to_become = ident_to_edit.__copy()
                            to_become.state = (self.state - 1) % 6

                            # write to matrix in the future
                            to_write_to = w.hex_matrix[left_neighbor.matrix_index][left_neighbor.list_index]
                            to_write_to.idents.append(to_become)

                            # remove any existing ident(s) in the future with the same serial number
                            # NOTE: may need to addendum to only be a nonmoving hex
                            trouble = next((Ident for Ident in w.ident_list if (Ident.serial_number == to_become.serial_number) and (Ident.state == -1)), None)
                            if trouble is not None:
                                w.ident_list.remove(trouble)
                            trouble = next((Ident for Ident in to_write_to.idents if (Ident.state == -1)), None)
                            if trouble is not None:
                                to_write_to.idents.remove(trouble)
                            w.ident_list.append(to_become)


                            # check the length of to write to idents and if it is longer than 1 now, average them! :)
                            print("LEFT testing ident length...")
                            if(len(to_write_to.idents) == 2) and (to_write_to.idents[0] in w.ident_list) and (to_write_to.idents[1] in w.ident_list):
                                print("LEFT CALL: Overlapping influences on stationary hex!!!")
                                to_add = None
                                if to_write_to.idents[0].state == (to_write_to.idents[1].state + 3) % 6:
                                    # they are opposites, keep the hex stationary
                                    to_add = to_write_to.idents[0].__copy()
                                    to_add.state = -1
                                # else if they are 120 degrees apart
                                elif (to_write_to.idents[0].state == (to_write_to.idents[1].state + 2) % 6):
                                    to_add = to_write_to.idents[0].__copy()
                                    to_add.state = (to_write_to.idents[0].state - 1) % 6
                                elif (to_write_to.idents[0].state == (to_write_to.idents[1].state + 4) % 6):
                                    to_add = to_write_to.idents[0].__copy()
                                    to_add.state = (to_write_to.idents[0].state + 1) % 6
                                # else if they are 60 degrees apart <- NOTE idk if this ever actually happens
                                else:
                                    pass
                                w.ident_list.remove(to_write_to.idents[0])
                                w.ident_list.remove(to_write_to.idents[1])
                                to_write_to.idents.clear()
                                if (to_add is not None):
                                    to_write_to.idents.append(to_add)
                                    w.ident_list.append(to_add)

                    if right_neighbor is not None:
                        ident_to_edit = right_neighbor.contains_direction(-1)
                        if (ident_to_edit is not None) and (len(right_neighbor.idents) == 1):
                            # if the right neighbor of the original stationary wall is also stationary, make it move
                            to_become = ident_to_edit.__copy()
                            to_become.state = (self.state + 1) % 6

                            to_write_to = w.hex_matrix[right_neighbor.matrix_index][right_neighbor.list_index]
                            to_write_to.idents.append(to_become)

                            trouble = next((Ident for Ident in w.ident_list if (Ident.serial_number == to_become.serial_number) and (Ident.state == -1)), None)
                            if trouble is not None:
                                w.ident_list.remove(trouble)
                            trouble = next((Ident for Ident in to_write_to.idents if (Ident.state == -1)), None)
                            if trouble is not None:
                                to_write_to.idents.remove(trouble)
                            w.ident_list.append(to_become)


                            print("RIGHT testing ident length...")
                            if(len(to_write_to.idents) == 2) and (to_write_to.idents[0] in w.ident_list) and (to_write_to.idents[1] in w.ident_list):
                                print("RIGHT CALL: Overlapping influences on stationary hex!!!")
                                if to_write_to.idents[0].state == (to_write_to.idents[1].state + 3) % 6:
                                    # they are opposites, keep the hex stationary
                                    to_add = to_write_to.idents[0].__copy()
                                    to_add.state = -1
                                # else if they are 120 degrees apart
                                elif (to_write_to.idents[0].state == (to_write_to.idents[1].state + 2) % 6):
                                    to_add = to_write_to.idents[0].__copy()
                                    to_add.state = (to_write_to.idents[0].state - 1) % 6
                                elif (to_write_to.idents[0].state == (to_write_to.idents[1].state + 4) % 6):
                                    to_add = to_write_to.idents[0].__copy()
                                    to_add.state = (to_write_to.idents[0].state + 1) % 6
                                # else if they are 60 degrees apart <- NOTE idk if this ever actually happens
                                else:
                                    pass
                                w.ident_list.remove(to_write_to.idents[0])
                                w.ident_list.remove(to_write_to.idents[1])
                                to_write_to.idents.clear()
                                if (to_add is not None):
                                    to_write_to.idents.append(to_add)
                                    w.ident_list.append(to_add)
                

    ##########################################################################################################

    
    def __neighbor_contains_direction(self, neighbor_state, neighbor_index=None):
        '''
        If the head-on (direction of self.state) neighboring hex contains an ident with the given direction, returns said ident
        Else returns None
        :param neighbor_state: int, the direction being queried
        :param neighbor_index: an int indicating the direction relative to self's location of the neighbor in question
        '''
        
        # Default value
        if neighbor_index == None:
            neighbor_index = self.state
        try:
            return self.__get_neighbor(self.world.hex_matrix, neighbor_index).contains_direction(neighbor_state)
        except:
            print("Neighbor DNE")
            return None

    ##########################################################################################################

    def __neighbor_is_wall(self, neighbor_index_offset=0):
        '''
        If the neighbor in the direction in which the ident is pointing is a wall, returns that ident; else returns None
        :param neighbor_index_offset: an int indicating the direction of the neighbor in question relative to self's direction
        '''
        neighbor_index = (self.state + neighbor_index_offset)%6

        return self.__neighbor_contains_direction(-2, neighbor_index)
        
    ##########################################################################################################
    
    def __head_on_collision(self):
        '''If there will be a head-on-collision, returns the ident with which it will collide; else returns none'''
        return self.__neighbor_contains_direction((self.state + 3)%6)

    ##########################################################################################################
    
    def rotate_adopt(self, future_hex, future_ident_list, dir_offset: int = 3, dir_final : int =-3):
        '''
        Copies self and rotates it by the indicated number of directions
        Adopts said rotated ident
        Returns rotated ident
        :param future_hex: the Hex in which self's copy will be located
        :param future_ident_list: the list in which self's copy will be located
        :param dir_offset: int, how much to rotate self's copy
        :param dir_final: int, the direction in which self's copy should point
        '''
        
        # Calculate final direction if none is given
        if dir_final == -3:
            dir_final = (self.state + dir_offset)%6

        ident = self.__copy()
        ident.state = dir_final

        # This is necessary for moving hexes colliding with stationary hexes
        ident.matrix_index = future_hex.matrix_index
        ident.list_index = future_hex.list_index

        if future_ident_list == self.world.corrected_idents:
            # Don't double-up on idents with the same serial number in the corrected list
            ident.remove_repeats(future_ident_list)

        future_ident_list.append(ident)

        # Don't double-up on idents with the same serial number in the same hex
        ident.remove_repeats(future_hex.idents)
        future_hex.idents.append(ident)

        if self in self.world.agents:
            print("swapping out agents")
            self.world.swap_agents(self, ident)

        return ident

    ##########################################################################################################
    
    
    def advance_or_flip(self):
        '''
        If an ident is stationary or a wall, writes this value to the hex_matrix_new
        Elif an ident is running into a wall or a head-on collision, flips it in place (writing to hex_matrix_new)
        Else advances an ident by one hex in its direction of motion (if that hex exists)
        '''
        
        future_matrix = self.world.hex_matrix_new
        future_hex = future_matrix[self.matrix_index][self.list_index]
        future_list = self.world.ident_list_new
    
        # Maintain stationaries and return
        if self.state == -1:
            my_copy = self.__copy()

            future_list.append(my_copy)
            future_hex.idents.append(my_copy)

            if self in self.world.agents:
                self.world.swap_agents(self, my_copy)

            return

        # If need to bounce head-on off of a wall, then bounce and return
        head_on_wall = self.__neighbor_is_wall() and not (self.__neighbor_is_wall(1) or self.__neighbor_is_wall(-1))
        double_adjacent_wall = self.__neighbor_is_wall(1) and self.__neighbor_is_wall(-1)
        if head_on_wall or double_adjacent_wall:
            
            self.rotate_adopt(future_hex, future_list)
            
            return


        # If need to bounce diagonally off of a wall, then bounce and return
        if self.__neighbor_is_wall(-1):
            self.rotate_adopt(future_hex, future_list, dir_offset=1)

            return
        
        # Other diagonal wall bounce case
        if self.__neighbor_is_wall(1):
            self.rotate_adopt(future_hex, future_list, dir_offset=-1)

            return
                
        # If need to bounce head-on off of another ident, then bounce and return
        if self.__head_on_collision():
            self.rotate_adopt(future_hex, future_list)

            return

        # Advance all others (if the location where they would advance to exists)
        future_neighbor = self.__get_neighbor(future_matrix, self.state)
        if future_neighbor:
            print("advance to future neighbor")
            copy_to_move = self.__copy()
            copy_to_move.matrix_index = future_neighbor.matrix_index
            copy_to_move.list_index = future_neighbor.list_index
                
            future_list.append(copy_to_move)
            future_neighbor.idents.append(copy_to_move)

            if self in self.world.agents:
                self.world.swap_agents(self, copy_to_move)


    ##########################################################################################################

    def visited(self, m, l):
        '''
        Marks ident as visited
        :param m: int, matrix_index
        :param l: int, list_index
        '''
        # push onto stack history
        # pushed onto the history is
            # hex matrix index
            # hex list index
            # current state

        # note, we want to keep up to 5 past states at a time
        # to change amount, just change limit #
        limit = 5

        if len(self.hist) == limit + 1:
            self.hist.pop(0)
        
        
        self.hist.append((m, l, self.state))


    ##########################################################################################################

    def __copy(self):
        '''Copies and returns self'''
        new_copy = Ident(self.matrix_index, self.list_index, self.world, color = self.color, state = self.state, serial_number = self.serial_number, hist = self.hist.copy(), property = self.property, agent=self.agent)
        return new_copy
    

    ##########################################################################################################
    
    def copy(self):
        '''Public version of __copy()'''
        return self.__copy()

    ###############################################################################################################

    def backstep(self):
        '''Reverts self to its state and location from one frame prior'''

        past = self.hist.pop()

        # first we change the state to the state it was at that point in time
        self.state = past[2]
        # then we put the ident into the hex it was before
        self.matrix_index = past[0]
        self.list_index = past[1]
    


    ###############################################################################################################

    def find_closest_goal(self, hex_test):
        '''
        Finds and returns the goal closest to self
        :param hex_test: the Hex relative to which distance is calculated (the Hex self is in)
        '''

        assert type(hex_test) is Hex

        goals = self.world.goals
        goal_distances = {}
        for goal in goals:
            dist = World.axial_distance(goal, hex_test)
            goal_distances[goal] = dist

        # return goal corresponding to minimum distance in the dictionary
        min_value = min(goal_distances.values())

        return min_value


    @staticmethod
    def find_next_move(agent):
        '''Finds and returns the agent's next move represented by an integer (0, 1, -1)''' 
        
        assert type(agent) == Ident

        # return value depending on the distance to the nearest goal from the hexes in the current agent's direction

        w = agent.world
        dir = agent.state
        goals = w.goals

        if len(goals) == 0:
            return 0

        assert dir is not None
        # print(dir)

        # find the forward, clockwise, and counterclockwise neighbor of our agent
        # NOTE: get neighbor returns the hex, not the ident
        n_forward = agent.get_neighbor(w.hex_matrix, dir % 6)
        n_right = agent.get_neighbor(w.hex_matrix, (dir + 1)%6)
        n_left = agent.get_neighbor(w.hex_matrix, (dir - 1)%6)

        # find the distance to the closest goal from each neighbor
        distances = {}
        if n_forward is not None:
            distances[n_forward] = agent.find_closest_goal(n_forward)
        if n_right is not None:
            distances[n_right] = agent.find_closest_goal(n_right)
        if n_left is not None:
            distances[n_left] = agent.find_closest_goal(n_left)

        assert distances is not None
        assert len(distances.values()) != 0

        min_distance = min(distances.values())

        to_go = next((Ident for Ident in distances.keys() if distances[Ident] == min_distance), None)

        if to_go == n_left:
            return -1
        elif to_go == n_right:
            return 1
        else:
            return 0
        
    
    @staticmethod
    def get_next_move(agent):
        '''Adjust's agent's state based on its next move'''

        assert agent in agent.world.agents
        assert agent in agent.world.ident_list

        w = agent.world
        my_index = w.agents.index(agent)

        influence = Ident.find_next_move(agent)


        # NOTE: If the agent is currently stationary, it cannot act
        if agent.state >= 0:
            agent.state += influence
            agent.state %= 6


    
###############################################################################################################

# hex class is just for graphics/displaying the board/storing idents
class Hex:
    # Default color (no idents): light blue
    DEFAULT_COLOR =(190, 240, 255)

    ##########################################################################################################

    def get_ident_index(self, to_find):
        '''
        Checks where a specific ident occurs within this hex's list
        If it contains the ident, returns the index
        Else returns -1
        :param to_find: the Ident to check for
        '''

        for i in range(len(self.idents)):
            if self.idents[i] == to_find:
                return i
        return -1

    ###############################################################################################################

    @staticmethod
    def __create_coor(x, y):
        '''
        Takes x and y (Cartesian coordinates where (0, 0) is the top left corner)
        Returns a list of 6 coordinates defining a hexagon
        '''
        # Making hex smaller so that borders will be visible
        return [(x+3, y+3), (x+37, y+3), (x+57, y+35), (x+37, y+67), (x+3, y+67), (x-17, y+35)]

    ##########################################################################################################

    def __init__(self, matrix_index, list_index):
        '''
        Hex constructor
        :param matrix_index: int, the index of the list of world.hex_matrix in which the Hex is located
        :param list_index: int, the index of world.hex_matrix[matrix_index] at which the Hex is located
        '''
        self.matrix_index = matrix_index
        self.list_index = list_index

        # Store relevant idents
        self.idents = []

        # Map matrix_index and list_index to Cartesian coordinates
        self.x = 60*matrix_index - 20
        self.y = 35*matrix_index + 70*list_index - 490

        self.coordinates = Hex.__create_coor(self.x, self.y)

       
        # Create arrows for later use
        #pivot is the center of the hexagon
        pivot = pygame.Vector2(self.x + 20, self.y + 35)
        # set of arrow points should be the vectors from the pivot to the edge points of the arrow
        arrow = [(0, -15), (10, -5), (5, -5), (5, 15), (-5, 15), (-5, -5), (-10, -5)]
        # get arrow by adding all the vectors to the pivot point => allows for easy rotation
        self.arrows = []
        for i in range(6):
            self.arrows.append([(pygame.math.Vector2(x, y)).rotate(60.0*i) + pivot for x, y in arrow]) 
    
        # Coordinates used to draw smaller hexagon later if the hex becomes stationary
        self.small_hexagon = [(self.x+9, self.y+11), (self.x+31, self.y+11), (self.x+47, self.y+35), (self.x+31, self.y+59), (self.x+9, self.y+59), (self.x-7, self.y+35)]
    ##########################################################################################################

    def is_moving(self):
        '''Returns a boolean indicating if the given hex contains any moving idents'''

        for ident in self.idents:
            if ident.state >= 0:
            # if (ident.state != -1) and (ident.state != -2):
                return True
        
        return False
    
    ##########################################################################################################

    def make_wall(self, world, list_to_append):
        '''Gives the designated hex a wall identity'''

        wall_ident = Ident(self.matrix_index, self.list_index, world, color = (0,0,0), state = -2)
        self.idents.append(wall_ident)
        list_to_append.append(wall_ident)

    ##########################################################################################################

    def make_goal(self, world, list_to_append):
        '''Gives the designated hex a goalpost identity'''

        goal_ident = Ident(self.matrix_index, self.list_index, world, color = (247, 173, 45), state = -1, serial_number = -1, hist = None, property = "goal")
        self.idents.append(goal_ident)
        list_to_append.append(goal_ident)

    ##########################################################################################################

    def contains_property(self, prop):
        '''
        Checks if a hex contains an ident with a specified property and returns that ident
        Else, returns none
        :param prop: string, the property for which to check
        NOTE: This could cause bugs if a hex contains multiple idents with the same property
        '''
        for ident in self.idents:
            if ident.property == prop:
                return ident
            
        return None

    ##########################################################################################################

    def contains_direction(self, dir: int):
        '''
        Checks if a hex contains an ident heading in the given directon and returns that ident; else returns None
        :param dir: int, the direction for which to check
        NOTE: This could cause bugs if a hex contains multiple idents with the same direction
        '''

        for ident in self.idents:
            if ident.state == dir:
                return ident

        return None
    
    ##########################################################################################################
    
    def contains_stationary(self):
        '''
        Checks if a hex contains a stationary ident and returns that ident; else returns None
        NOTE: This could cause bugs if a hex contains multiple stationary idents
        '''

        return self.contains_direction(-1)
    
    ##########################################################################################################
    
    @staticmethod
    def condense(my_list):
        '''
        Returns a list containing only the truthy objects in the passed list
        :param my_list: the non-minimized list
        '''
        returnable = []

        for object in my_list:
            if object:
                returnable.append(object)
        
        return returnable

    ##########################################################################################################

    def check_superimposition(self, world, ident_to_check):
        '''
        Resolves cases of superimposition caused by steps backward in resolve_collisions() (ex. bumps into stationary idents)
        :param world: the World in which self is located
        :param ident_to_check:
        '''

        # All the hexes in this list should contain at least one ident
        assert len(self.idents)

        # If the hex only contains one ident, that's fine
        if len(self.idents) == 1:
            print("no superimposition to resolve")
            return

        # Create a hex to store our updates
        corrected_hex = Hex(self.matrix_index, self.list_index)

        # Create sorted list of moving idents in hex (including the ident we're checking)
        moving_idents = [None]*6
        for ident in self.idents:
            if ident.state >= 0:
                moving_idents[ident.state] = ident
        
        # And create a list of moving idents without null spacers
        condensed_list = Hex.condense(moving_idents)

        # If the hex contains a mix of stationary and moving idents, handle it
        if self.contains_stationary():
            print("hex with mixed superimposition")
            
            # If said stationary hex is the ident we're checking:
            if ident_to_check.state == -1:
                
                # and if there is only one moving ident in the hex, take its state and make it stationary, pushing its newly stationary self to the checkable list
                if len(condensed_list) == 1:
                    
                    # Make moving hex stationary and push it to be dealt with
                    moving_hex_of_origin = condensed_list[0].get_neighbor(world.hex_matrix, (condensed_list[0].state + 3)%6)
                    modified_ident = condensed_list[0].rotate_adopt(moving_hex_of_origin, world.corrected_idents, dir_final=-1)
                    world.double_check.append([moving_hex_of_origin, modified_ident])

                    # Make stationary ident (ident_to_check) move
                    ident_to_check.rotate_adopt(corrected_hex, world.corrected_idents, dir_final = condensed_list[0].state)
                                    
                # else do nothing (the necessary bouncing has already happened)
                else:
                    return
            
            # Else bounce the ident we're checking off of the stationary hex
            else:
                ident_to_check.rotate_adopt(corrected_hex, world.corrected_idents)


        # If the hex contains multiple moving idents, bounce them off of one another as necessary
        else:
            
            # If the hex contains opposite pairs of idents, remove said pairs from the moving_idents list
            for i in range(3):
                if moving_idents[i] and moving_idents[i+3]:

                    # If one of these opposite idents is the one we're checking, bounce them off of one another
                    if (i == ident_to_check.state) or (i + 3 == ident_to_check.state):
                        moving_idents[i].rotate_adopt(corrected_hex, world.corrected_idents)
                        moving_idents[i+3].rotate_adopt(corrected_hex, world.corrected_idents)
                    
                    # Else these idents will already have been bounced off of one another, so we only have to preserve them
                    else:
                        # Don't double-up on idents with the same serial number in the same hex
                        # NOTE: I'm not sure if this would ever be an issue
                        moving_idents[i].remove_repeats(corrected_hex.idents)
                        corrected_hex.idents.append(moving_idents[i].copy())
                        
                        moving_idents[i+3].remove_repeats(corrected_hex.idents)
                        corrected_hex.idents.append(moving_idents[i+3].copy())


                    # Erase the rotated idents from our running log
                    moving_idents[i] = None
                    moving_idents[i+3] = None
            
            condensed_list = Hex.condense(moving_idents)
            remaining_idents = len(condensed_list)
            
            # If there is only one ident remaining, preserve it

            if remaining_idents == 1:
                my_copy = condensed_list[0].copy()     

                # Don't double-up on idents with the same serial number in the same hex
                # NOTE: I'm not sure if this would ever be an issue
                my_copy.remove_repeats(corrected_hex.idents)
                corrected_hex.idents.append(my_copy)
                
                # Don't double-up on idents with the same serial number in the corrected list
                my_copy.remove_repeats(world.corrected_idents)

                world.corrected_idents.append(my_copy)

            # For everything in check_superimposition from here on down, we need to account for ident_to_check either being or not being involved in the potential collision
            # If ident_to_check is involved, deal with it. Otherwise, leave it be (it's already been handled, and messing with it would only undo that work)
            elif remaining_idents == 3:
                # There are three idents remaining
                
                # If the three idents remaining are at 120 degrees to one another, they all bounce off in the opposite direction
                if (condensed_list[0].find_offset(condensed_list[1]) == 2) and (condensed_list[0].find_offset(condensed_list[2]) == 2):
                    condensed_list[0].rotate_adopt(corrected_hex, world.corrected_idents)
                    condensed_list[1].rotate_adopt(corrected_hex, world.corrected_idents)
                    condensed_list[2].rotate_adopt(corrected_hex, world.corrected_idents)

                # Else (if the three idents remaining are at 60 degrees to one another), the two on the sides swap states and the one in the middle stays the same
                else:
                    for i in range(6):
                        if moving_idents[i] and moving_idents[(i+1)%6] and moving_idents[(i+2)%6]:
                            # The two outer idents swap states
                            moving_idents[i].rotate_adopt(corrected_hex, world.corrected_idents, dir_final = moving_idents[(i+2)%6].state)
                            moving_idents[(i+2)%6].rotate_adopt(corrected_hex, world.corrected_idents, dir_final = moving_idents[i].state)

                            # The middle ident is preserved
                            middle_copy = moving_idents[(i+1)%6].copy()
                            middle_copy.remove_repeats(corrected_hex.idents)
                            corrected_hex.idents.append(middle_copy)

                            # Don't double-up on idents with the same serial number in the corrected list
                            my_copy.remove_repeats(world.corrected_idents)

                            world.corrected_idents.append(middle_copy)
            
            else:
                assert remaining_idents == 2

                # If there are only two idents remaining, they take one another's states
                condensed_list[0].rotate_adopt(corrected_hex, world.corrected_idents, dir_final = condensed_list[1].state)
                condensed_list[1].rotate_adopt(corrected_hex, world.corrected_idents, dir_final = condensed_list[0].state)

            print("hex with moving-only superimposition")
        
        # Add the updated hex to corrected_hexes
        world.corrected_hexes.append(corrected_hex)


    ##########################################################################################################

    def draw(self, screen):
        '''
        Graphics (drawing hexes and the corresponding idents)
        :param screen: surface on which to draw
        '''
            
        color_to_draw = Hex.DEFAULT_COLOR


        if (len(self.idents) >= 1):
            # If a hex contains only one ident, take that color
            # If a hex contains multiple idents, the ident stored first will be the outermost color
            color_to_draw = self.idents[0].color
        
        # Draw the hexagon
        pygame.draw.polygon(screen, color_to_draw, self.coordinates)

        # Draw an extra hexagon to visually show that a hexagon is stationary even with the different colors
        if self.contains_direction(-1) != None:
            new_color = [max(0, c - 120) for c in color_to_draw]
            pygame.draw.polygon(screen, new_color, self.small_hexagon)

        if self.contains_property("goal"):
            pygame.draw.polygon(screen, (255, 230, 155), self.small_hexagon)
    
        # Draw multiple nesting circles indicating colors for hexes with superimposed idents/states
        for i in range(1, len(self.idents)):
            if (33 - 5*i) > 0:
                pygame.draw.circle(screen, self.idents[i].color, (self.x+20, self.y+35), 33-5*i)
    
        # Draw an arrow on the hex if the hex is moving
        if self.is_moving():
            for i in range(6):
                if self.contains_direction(i):
                    pygame.draw.polygon(screen, (0, 0, 0), self.arrows[i])

    ##########################################################################################################

###############################################################################################################

# for setting initial state of the world / having a student interact
# while loop for running game goes in World
class World:

    def __init__(self, automatic_walls=True, display_window=True):
        '''
        World constructor
        :param automatic_walls=True: boolean, whether or not walls will be included around the displayed area
        :param display_window=True: boolean, whether or not to show graphics
        '''

        self.goalEnd = False

        self.frames_created = 0

        pygame.init()

        SCREEN_WIDTH = 800

        SCREEN_HEIGHT = 600

        # NOTE: If the user is poorly-behaved (says they don't want to display but later does), this will cause issues due to the lack of self.screen
        if display_window:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            pygame.display.set_caption("Hex Simulator")

        # Set up hex matrix
        self.hex_matrix = []

        for x in range(15):
            hex_list = []
            self.hex_matrix.append(hex_list)

            for y in range(16):
                myHex = Hex(x, y)
                hex_list.append(myHex)
        
        # Set up new hex matrix
        self.hex_matrix_new = []

        for x in range(len(self.hex_matrix)):
            hex_list_new = []
            self.hex_matrix_new.append(hex_list_new)

            for y in range(len(self.hex_matrix[x])):
                myHex = Hex(x, y)
                hex_list_new.append(myHex)

        # Set up ident list
        self.ident_list = []

        # Set up new ident list
        self.ident_list_new = []

        # Set up wall list
        self.wall_list = []

        # Set up list of hex-ident pairs to double-check and lists to store the corrections
        self.double_check = []
        self.corrected_hexes = []
        self.corrected_idents = []

        # Default agent to None (will be assigned a value in __read_line if one exists)
        self.agents = []

        # set up goalpost list
        self.goals = []
        
        # Create walls around the edges, if requested
        if automatic_walls:
            # Left edge
            for hex in self.hex_matrix[0]:
                hex.make_wall(self, self.wall_list)
            # Right edge
            for hex in self.hex_matrix[13]:
                hex.make_wall(self, self.wall_list)
            for i in range(6):
                # Top edge
                self.hex_matrix[1+2*i][6-i].make_wall(self, self.wall_list)
                self.hex_matrix[2+2*i][6-i].make_wall(self, self.wall_list)

                # Bottom edge
                self.hex_matrix[1+2*i][15-i].make_wall(self, self.wall_list)
                self.hex_matrix[2+2*i][14-i].make_wall(self, self.wall_list)


    # from https://www.redblobgames.com/grids/hexagons/
    @staticmethod
    def axial_subtract(a : Hex, b : Hex):
        '''Method for determining the axial hex distance between two hexes in a hex world'''

        return Hex(a.matrix_index - b.matrix_index, a.list_index - b.list_index)

    ##########################################################################################################

    # from https://www.redblobgames.com/grids/hexagons/
    @staticmethod
    def axial_distance(a : Hex, b : Hex):
        '''Method for determining the axial hex distance between two hexes in a hex world'''

        vec = World.axial_subtract(a, b)
        return (abs(vec.matrix_index)
            + abs(vec.matrix_index + vec.list_index)
            + abs(vec.list_index)) / 2
    
    ##########################################################################################################
    
    def swap_agents(self, agent_to_remove, agent_to_append):
        '''
        Swaps out one agent for another in the agent list
        :param agent_to_remove:
        :param agent_to_append:
        '''
        assert agent_to_remove.serial_number == agent_to_append.serial_number
        self.agents.remove(agent_to_remove)
        self.agents.append(agent_to_append)
    
    ##########################################################################################################
    
    @classmethod
    def __get_color(self, color_text):
        '''
        Returns color corresponding to passed string
        :param color_text: string color name
        '''

        if color_text == "YELLOW" or color_text == "YELLOW\n":
            return (255, 255, 102)
        elif color_text == "PURPLE" or color_text == "PURPLE\n":
            return (204, 0, 255)
        elif color_text == "ORANGE" or color_text == "ORANGE\n":
            return (255, 102, 0)
        elif color_text == "GREEN" or color_text == "GREEN\n":
            return (106, 232, 100)
        elif color_text == "BLUE" or color_text == "BLUE\n":
            return (45, 70, 181)
        elif color_text == "CYAN" or color_text == "CYAN\n":
            return (71, 230, 216) 
        elif color_text == "RED" or color_text == "RED\n":
            return (219, 24, 24)
        elif color_text == "MAROON" or color_text == "MAROON\n":
            return (143, 6, 15)
        elif color_text == "PINK" or color_text == "PINK\n":
            return (230, 57, 129)
        elif color_text == "BROWN" or color_text == "BROWN\n":
            return (166, 129, 85)
        else:
            return (100, 100, 100)

    ##########################################################################################################
    
    def __draw(self):
        '''Draws world'''
        # Reset screen
        self.screen.fill((0, 0, 0))

        # Draw all hexes with idents
        for hex_list in self.hex_matrix:
            for hex in hex_list:
                hex.draw(self.screen)

    ##########################################################################################################

    def update(self):
        '''Advances world by one frame'''

        # Clear list of hexes to double-check for superimposed idents
        self.double_check.clear()

        # Clear lists of corrected hexes and idents
        self.corrected_hexes.clear()
        self.corrected_idents.clear()

        # Push history of idents, walls, and goals
        for ident in self.ident_list:
            ident.visited(ident.matrix_index, ident.list_index)
        
        for wall in self.wall_list:
            wall.visited(wall.matrix_index, wall.list_index)

        for goal in self.goals:
            goal.visited(goal.matrix_index, goal.list_index)
        
        # Agents act
        for agent in self.agents:
            print("agent state was " + str(agent.state))
            Ident.get_next_move(agent)
            print("agent state is now " + str(agent.state))


        # Clear the new matrix and list so that advance_or_flip can write to it
        for hex_list in self.hex_matrix_new:
            for hex in hex_list:
                # Save wall_ident to add back in, if applicable
                wall_ident = hex.contains_direction(-2)
                # also save and add back in goalposts
                goal_ident = hex.contains_property("goal")
                
                hex.idents.clear()
                
                if wall_ident:
                    self.hex_matrix_new[wall_ident.matrix_index][wall_ident.list_index].idents.append(wall_ident)
                if goal_ident:
                    self.hex_matrix_new[goal_ident.matrix_index][goal_ident.list_index].idents.append(goal_ident)
                    print("goal ident added to hex matrix new")
        
        self.ident_list_new.clear()

        # Move or flip all idents (except for walls)
        for ident in self.ident_list:
            ident.advance_or_flip()

        # Clear the current matrix and list so that resolve_collisions can write to it
        for hex_list in self.hex_matrix:
            for hex in hex_list:
                # Save wall_ident to add back in, if applicable
                wall_ident = hex.contains_direction(-2)
                # also save and add back in goalposts
                goal_ident = hex.contains_property("goal")
                
                hex.idents.clear()
                
                if wall_ident:
                    self.hex_matrix[wall_ident.matrix_index][wall_ident.list_index].idents.append(wall_ident)
                if goal_ident:
                    self.hex_matrix[goal_ident.matrix_index][goal_ident.list_index].idents.append(goal_ident)
                    print("goal ident added to hex matrix after advance/flip")
        
        self.ident_list.clear()
                
        # Fix collisions in all idents (except for walls)
        for ident in self.ident_list_new:
            ident.resolve_collisions()

        # Fix issues caused by moving idents backwards when moving idents collide with stationary idents and step back
        while len(self.double_check):
            hex_and_ident = self.double_check.pop()
            check_hex = hex_and_ident[0]
            check_ident = hex_and_ident[1]
            check_hex.check_superimposition(self, check_ident)
        
        # Substitute in corrected hexes and idents
        for hex in self.corrected_hexes:
            print("swap in corrected hex")
            self.hex_matrix[hex.matrix_index][hex.list_index] = hex

        for new_ident in self.corrected_idents:
            new_ident.remove_repeats(self.ident_list)
        
        for new_ident in self.corrected_idents:
            print("appending new ident with serial number " + str(new_ident.serial_number) + " and state " + str(new_ident.state))

            self.ident_list.append(new_ident)

        self.frames_created += 1

        print(str(self.frames_created))

    ##########################################################################################################

    def __backstep(self):
        '''Reverts every hex to how it was one state back.'''
        # Each ident holds its own history of the past 5 steps at any given time.
        # Because the code is deterministic, the next step will be re-calculated the same way.
        
        # Only take any steps if there is history left to be shown
        if (len(self.ident_list) > 0) and (len(self.ident_list[0].hist) > 0):
        
            # First, clear the matrix and list
            for hex_list in self.hex_matrix:
                for hex in hex_list:

                    # Walls are managed separately to other idents, so re-draw them from their own list
                    wall_ident = hex.contains_direction(-2)
                    goal_ident = hex.contains_property("goal")

                    hex.idents.clear()

                    if wall_ident:
                        self.hex_matrix[wall_ident.matrix_index][wall_ident.list_index].idents.append(wall_ident)
                    if goal_ident:
                        self.hex_matrix[goal_ident.matrix_index][goal_ident.list_index].idents.append(goal_ident)

                    # also redraw the goalpost idents separately

            # Then, apply step back on all idents
            # After applying the step back, return those idents to the list in their respective hexes
            for ident in self.ident_list:
                ident.backstep()

                self.hex_matrix[ident.matrix_index][ident.list_index].idents.append(ident)
              

            for wall in self.wall_list:
                # wall.backstep()
                self.hex_matrix[wall.matrix_index][wall.list_index].idents.append(wall)

                ident.world.hex_matrix[ident.matrix_index][ident.list_index].idents.append(ident)

            # agents (if they exist) must be set back one index spot so they step forward the same
            if len(self.agents):
                for i in range (len(self.agent_step_indices)):
                    self.agent_step_indices[i] -= 1
                    self.agent_step_indices[i] %= len(self.agent_choices[i])
            
            self.frames_created -= 1

        # If there are no previous states to step back to, print an error message
        else:
            print("Maximum steps back have been taken.")

    ##########################################################################################################

    def run(self):
        '''Runs simulation'''
        
        run = True

        state = "pause"
        clock = pygame.time.Clock()
        dt = 0

        while run and (not self.goalEnd):

            # Event handler (closing window)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    run = False

                # the following takes in and reacts to keyboard input
                if event.type == pygame.TEXTINPUT:

                    # takes the key input
                    keys = pygame.key.get_pressed()

                    # changes state based on keyboard input
                        # g = "go" ; runs at normal speed
                        # p = "pause" ; stops
                        # h = "hyper" ; goes really fast
                    if keys[pygame.K_g]:
                        state = "go"
                    elif keys[pygame.K_p]:
                        state = "pause"
                    elif keys[pygame.K_h]:
                        state = "hyper"

                    # when in pause, you can step forward or back
                    if state == "pause" and keys[pygame.K_s]:
                        self.update()

                        pygame.time.delay(100)
                        # Take one second pause

                    if state == "pause" and keys[pygame.K_b]:
                        self.__backstep()

                        pygame.time.delay(100)
                        # Take one second pause
            
            self.__draw()

            # flips to the next frame
            pygame.display.flip()

            if state == "go":
                print("--------------------on go--------------------")
                dt = clock.tick(2) / 1000
                self.update()
            elif state == "hyper":
                dt = clock.tick(20) / 1000
                self.__update()
        
        # Exit
        if(self.goalEnd):
            print()
            print("SIM OVER, WE HIT GOAL")
            self.screen.fill((200, 200, 200))
            
            print()   
            print("It took " + str(self.frames_created) + " frames to get into the goal.")
            pygame.display.update()
            while(self.goalEnd):
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.goalEnd = False
        pygame.quit()

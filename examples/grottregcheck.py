# coding: utf-8



class GrottRegChecker:
    """ 
    Performs register checks as they are described in the
    modbus protocol documentation
    
    In verbose mode will print a JSON strings compatible with the Grott
    layout format
    
    Tested with data from packets: T060104X & T060103X - the latter however,
        needs 4 bytes ofset after position 125 in order to align with the 
        documentation (the offset is controlled via the apply_2b_offset property)
        
    This tools is based on Growatt Inverter Modbus RTU Protocol V1.20 from 28-Apr-2020
        and real data as seen by Grott
    
    Examples:
    >>> checker = GrottRegChecker('''...''')
    >>> checker.apply_2b_offset = True
    >>> checker.ascii_at(125, 132)
    {"value" :666, "length" : 10, "type" : "text"},
    'PV   80000'
    >>> checker.ascii_at(34, 42)
    {"value" :294, "length" : 16, "type" : "text"},
    '   PV Inverter  '
    >>> checker.int_at(45)
    {"value" :338, "length" : 2, "type" : "num"},
    2022
    >>> checker.report
    True
    >>> checker.verbose
    True
    
    """
    
    data_start = 158
    """ Start of the modbus data in the pakcet
        Offset from the Grott plain data as seen in verbose mode 
    """
    second_group_offset = 2
    
    def __init__(self, hex_data: str):
        """

        :param hex_data: Grott plain data (from logging in verbose mode)
        """
        self.packet = ''.join([x.strip() for x in hex_data.split('\n')])
        self.debug = False
        self.verbose = False
        self.apply_2b_offset = False

    def int_at(self, register: int):
        """ Try to extract an integer from the provided position """
        start, end = self._reg_boundary(register)
        try:
            res = int(self.packet[start:end], 16)
            if self.verbose:
                print(f'{{"value" :{start}, "length" : 2, "type" : "num"}},')
            return res
        except Exception as e:
            print(e)
    
    def ascii_at(self, s_register: int, e_register: int):
        """
            Extract ASCII string from the data enclosed between the 
            start and end registers.

        :param s_register: Start of the ASCII string
        :param e_register: End register of the string. 
            Note: This should be the number at the start of the next row 
            after the ASCII definition in the documentation
        """
        start, end = self._reg_boundary(s_register, ascii_to=e_register)
        try:
            res_string = bytes.fromhex(self.packet[start:end])
            if self.verbose:
                print(f'{{"value" :{start}, "length" : {(end - start) // 2}, "type" : "text"}},')
            return res_string.decode()
        except Exception as e:
            print(e)
            
    def long_at(self, register: int):
        """ 
            Try extraction of a long signed integer from the sepcified
            register 
        """
        start, end = self._reg_boundary(register, long=True)
        try:
            res = int.from_bytes(bytes.fromhex(self.packet[start:end]), byteorder='big', signed=True)
            if self.verbose:
                print(f'{{"value" :{start}, "length" : 4, "type" : "numx"}},')
            return res
        except Exception as e:
            print(e)
                                 
    def _reg_boundary(self, x: int, long=False, ascii_to=None):
        """ 
            Transform the ID to start/end positions in the plain
            data
        """
        if self.apply_2b_offset and self.report and x > 124:
            """ Apply an offset when delaing with a report packet 
                and the register is above 124
            """
            x += self.second_group_offset
            if ascii_to:
                ascii_to += self.second_group_offset
        if ascii_to and ascii_to > 0:
            x_end = ascii_to * 2
            x = x * 2
            if self.debug:
                print(f'[{self.data_start + x*2}:{self.data_start + x_end * 2}]')
            return self.data_start + x*2, self.data_start + x_end*2
        else:
            x = x * 2
            if  long:
                x_end = x + 4
            else:
                x_end = x + 2
        if self.debug:
            print(f'[{self.data_start + x * 2}:{self.data_start + x_end * 2}]')
        return self.data_start + x * 2, self.data_start + x_end * 2
    
    @property
    def report(self) -> bool:
        """ True if we dealing with a report packet """
        return int(self.packet[14:16], 16) == 3
    

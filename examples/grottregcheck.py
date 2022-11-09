# coding: utf-8
import enum
from typing import Tuple


class InverterType(str, enum.Enum):
    MAC = 'mac'
    MAX = 'max'
    MID = 'mid'
    MIN = 'min'
    MIX = 'mix'
    SPA = 'spa'
    SPF = 'spf'
    SPH = 'sph'
    UNKNOWN = 'unk'

    @classmethod
    def _missing_(cls, value):
        return InverterType.UNKNOWN


class GrottRegChecker:
    """ 
    Performs register checks as they are described in the
    modbus protocol documentation
    
    In verbose mode will print a JSON strings compatible with the Grott
    layout format
    
    Tested with data from packets: T060104XMAX / T060103XMAX / T050104XMAX / T050104XMAX / SPF packet from the examples
        
    This tools is based on Growatt Inverter Modbus RTU Protocol V1.20 from 28-Apr-2020
        and real data as seen by Grott
    
    Examples:
    >>> checker = GrottRegChecker('''...''')
    >>> checker.ascii_at(125, 132)
    {"value" :666, "length" : 14, "type" : "text"},
    'PV   80000    '
    >>> checker.ascii_at(34, 42)
    {"value" :294, "length" : 16, "type" : "text"},
    '   PV Inverter  '
    >>> checker.int_at(45)
    {"value" :338, "length" : 2, "type" : "num"},
    2022
    >>> checker.verbose
    True
    >>> checker.inverter
    <InverterType.MAX: 'max'>
    
    """

    header_max_len = 158
    """ MAX header length. Scan this range for a register map """
    second_group_offset = 2
    
    def __init__(self, hex_data: str):
        """

        :param hex_data: Grott plain data (from logging in verbose mode)
        """
        self.packet = ''.join([x.strip() for x in hex_data.split('\n')])
        self.debug = False
        self.verbose = False
        self.apply_2b_offset = True  # Enabled by default
        self.data_start = 0
        self.inverter = self.inv_auto_detect()

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
            Try extraction of a long signed integer from the specified
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
        second_group = 44 if self.inverter == InverterType.SPF else 124
        x = self._translate_reg_to_pos(x)

        if self.apply_2b_offset and x > second_group:
            """ Always use 2 bytes offset  
                if the register is in the second group
            """
            x += self.second_group_offset
            if ascii_to:
                ascii_to = self._translate_reg_to_pos(ascii_to)
                ascii_to += self.second_group_offset

        if ascii_to:
            x_end = ascii_to * 2
            x = x * 2
            if self.debug:
                print(f'[{self.data_start + x*2}:{self.data_start + x_end * 2}]')
            return self.data_start + x*2, self.data_start + x_end*2
        else:
            x = x * 2
            if long:
                x_end = x + 4
            else:
                x_end = x + 2
        if self.debug:
            print(f'[{self.data_start + x * 2}:{self.data_start + x_end * 2}]')
        return self.data_start + x * 2, self.data_start + x_end * 2
    
    @property
    def report(self) -> bool:
        """ True if we are dealing with a report packet """
        return int(self.packet[14:16], 16) == 3

    @property
    def datapacket(self) -> bool:
        """ True if we are dealing with a datarecord """
        return int(self.packet[14:16], 16) == 4

    @property
    def buffered(self) -> bool:
        """ True if this is a buffered packet """
        return int(self.packet[14:16], 16) == 50

    def _in_header(self, hex_str: str) -> bool:
        """ Check for a hex sequence in the header of the packet
            Update the data_start property if the string is found
        """
        try:
            position = self.packet[:self.header_max_len].index(hex_str)
            self.data_start = position + 10
            return True
        except ValueError:
            return False
        except Exception as e:
            print(e)

    def inv_auto_detect(self) -> InverterType:
        """
        Inverter auto detection

        Register map values
        First group -> struct.pack('>bhh', 2, <range_start>, <range_end>).hex()
        Second group -> struct.pack('>hh', <range_start>, <range_end>).hex()
        """
        inv_default = InverterType.UNKNOWN
        if self.datapacket or self.buffered:
            if self._in_header('020bb80c34'):
                return InverterType.MIN
            if self._in_header('0203e80464'):
                return InverterType.SPA
            if self._in_header('020000002c'):
                return InverterType.SPF
            if self._in_header('020000007c'):
                """ All other for which the first group is in the range 0-124 """
                """ peek into the next map """
                next_map = self.data_start + 500  # 125 words * 4
                if self.packet[next_map:next_map+8] == '007d00f9':
                    if self.packet[7] == '5':
                        return InverterType.MID
                    elif self.packet[7] == '6':
                        return InverterType.MAX
                elif self.packet[next_map:next_map+8] == '03e80464':
                    """ CAN BE SPH/MIX - SPH seems more commonly used
                        Return SPH for now 
                    """
                    # TODO: Find the difference between SPH & MIX
                    return InverterType.SPH
        if self.report:
            if self._in_header('020000002c'):
                return InverterType.SPF
            elif self._in_header('020000007c'):
                """ All with first group 0-124 """
                next_map = self.data_start + 500
                if self.packet[next_map:next_map+8] == '0bb80c34':
                    return InverterType.MIN
                elif self.packet[next_map:next_map+8] == '007d00f9':
                    if self.packet[7] == '5':
                        return InverterType.MID
                    elif self.packet[7] == '6':
                        return InverterType.MAX
                elif self.packet[next_map:next_map+8] == '03e80464':
                    """ Need more info about the storage type inverters 
                        and their report (03) packet
                        MIX / SPA / SPH all use the [1000:1024] range 
                    """
                    # TODO: Find a way to distinguish between these types
                    return InverterType.UNKNOWN
        return inv_default

    def _translate_reg_to_pos(self, reg: int):
        """
        Translate a register to position
        Used by the _reg_boundary method to map a register to its
        actual position in the packet
        """
        """ Directly mapped """
        if self.inverter in [InverterType.MAX, InverterType.MID, InverterType.MAC]:
            return reg
        if self.inverter == InverterType.SPF:
            return reg

        """ Inverters which registers need translation """
        if self.inverter == InverterType.MIN:
            if self.report and reg <= 124:
                return reg
            elif self.report and reg >= 3000:
                return 125 + reg - 3000
            if self.datapacket or self.buffered:
                return reg - 3000

        if self.inverter in [InverterType.MIX, InverterType.SPA, InverterType.SPH]:
            if self.report:
                if reg <= 124:
                    return reg
                else:
                    return 125 + reg - 1000
            if self.datapacket or self.buffered:
                if self.inverter in [InverterType.MIX, InverterType.SPH]:
                    if reg <= 124:
                        return reg
                    else:
                        return 125 + reg - 1000
                elif self.inverter == InverterType.SPA:
                    if 1000 < reg <= 1124:
                        return reg - 1000
                    else:
                        return 125 + reg - 2000

        # Raise error in case that we have unhandled case
        raise ValueError(f'Unhandled inverter/register combination {self.inverter} -> {reg}')

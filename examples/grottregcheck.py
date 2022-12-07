# coding: utf-8
import enum
from typing import List
import struct


__DEBUG__ = False


class GrottDataMarker:
    """
    The data marker specifies the position in the packet
    where the registers <from_reg> <to_reg> are located
    """
    def __init__(self, pos, start, end):
        self.data_from = pos
        self.from_reg = start
        self.to_reg = end

    def __repr__(self):
        return f'<Marker @ [{self.data_from-8}-{self.data_from}]> reg: [{self.from_reg}:{self.to_reg}]'


class GrottConstants:

    MASK = b'Growatt'  # Encryption mask
    HEADER_PLAIN = 8  # Unencrypted
    HEADER_MAX_LEN = 158  # for packet in HEX format
    PACKET_CRC = -2  # Last 2 bytes


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


class InvalidRegister(Exception):
    """ Raised on invalid/unknow register ID """
    pass


class GrottRegChecker:
    """ 
    Performs register checks as they are described in the
    modbus protocol documentation
    
    In verbose mode will print a JSON strings compatible with the Grott
    layout format
    
    Tested with data from packets: T060104XMAX / T060103XMAX / T050104XMAX / T050104XMAX / SPF packet from the examples
        
    This tool is based on Growatt Inverter Modbus RTU Protocol V1.20 from 28-Apr-2020
        and real data as seen by Grott
    
    Examples:
    >>> checker = GrottRegChecker('''...''')
    >>> checker.ascii_at(125, 132)
    {"value" :666, "length" : 16, "type" : "text"},
    'PV   80000    '
    >>> checker.ascii_at(34, 41)
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

    second_group_offset = 2
    
    def __init__(self, hex_data: str):
        """

        :param hex_data: Grott plain data (from logging in verbose mode)
        """
        self.packet = ''.join([x.strip() for x in hex_data.split('\n')])
        self.debug = False
        self.verbose = False
        self.data_start = 0
        self.inverter = self.inv_auto_detect()
        if self.inverter != InverterType.UNKNOWN:
            self.regmaps = self.map_extractor()

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
        x = self._translate_reg_to_pos(x)

        if ascii_to:
            x_end = self._translate_reg_to_pos(ascii_to) + 4
            if self.debug:
                print(f'ASCII end at: {x_end}')
        else:
            if long:
                x_end = x + 8
            else:
                x_end = x + 4
            if self.debug:
                print(f'Int/Long end at: {x_end}')
        if self.debug:
            print(f'[{x}:{x_end}]')
        return x, x_end
    
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
        return int(self.packet[14:16], 16) == 80

    @property
    def has_third_map(self) -> bool:
        """ True if the first marker/register map is prefixed with 03 """
        return self.packet[self.data_start-10:self.data_start-8] == '03'

    def _in_header(self, hex_str: str) -> bool:
        """ Check for a hex sequence in the header of the packet
            Update the data_start property if the string is found
        """
        try:
            position = self.packet[:GrottConstants.HEADER_MAX_LEN].index(hex_str)
            self.data_start = position + 10
            return True
        except ValueError:
            return False
        except Exception as e:
            print(e)

    def map_extractor(self) -> List[GrottDataMarker]:
        """
        Extract the register maps from the packet
        """

        marker = self.data_start - 10
        reg_s, reg_e = struct.unpack('>hh', bytes.fromhex(self.packet[marker + 2:marker + 10]))
        num_registers = reg_e - reg_s + 1
        regs = [GrottDataMarker(marker + 10, reg_s, reg_e)]
        data_start = marker + 10

        while True:
            marker_next = num_registers * 4 + data_start
            if marker_next + 8 > len(self.packet):
                break
            if __DEBUG__:
                print(f'Searching for next map @ {marker_next}')
            reg_s, reg_e = struct.unpack('>hh', bytes.fromhex(self.packet[marker_next:marker_next + 8]))
            """ Mapping for the start:end register in this section """
            if reg_e > reg_s:
                regs.append(GrottDataMarker(marker_next + 8, reg_s, reg_e))
            data_start = marker_next + 8
            num_registers = reg_e - reg_s + 1

        return regs

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
            if self._in_header('030000002c') or self._in_header('020000002c'):
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
                    # If needed. The mapping is identical anyway
                    return InverterType.SPH
            if self._in_header('030000007c'):
                """ Definitely SPH. Thanks @"""
                return InverterType.SPH

        if self.report:
            if self._in_header('020000002c') or self._in_header('030000002c'):
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
                        MIX / SPA / SPH all use the [1000:1124] range 
                    """
                    # TODO: Find a way to distinguish between these types if needed
                    # As the packet contains the same data for these registers this seems unnecessary
                    return InverterType.SPH
            elif self._in_header('030000007c'):
                return InverterType.SPH

        return inv_default

    def _translate_reg_to_pos(self, reg: int):
        """
        Translate a register to position.

        Uses the new data markers. Much cleaner and accurate code
        """

        for _map in self.regmaps:
            if _map.from_reg <= reg <= _map.to_reg:
                reg_idx = [x for x in range(_map.from_reg, _map.to_reg + 1)].index(reg)
                if __DEBUG__:
                    print(f'GrottDataMarker pos: {_map.data_from + reg_idx * 4}')
                return _map.data_from + reg_idx * 4

        raise InvalidRegister(f'This packet has no register with ID <{reg}>')

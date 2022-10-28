# coding=utf-8

import logging
from itertools import cycle

from crc import modbus_crc

logger = logging.getLogger(__name__)

def to_hex(data):
    return "".join("\\x{:02x}".format(n) for n in data)

# encrypt / decrypt data.
def decrypt(decdata):
    ndecdata = len(decdata)

    # Create mask and convert to hexadecimal
    mask = "Growatt"
    hex_mask = ['{:02x}'.format(ord(x)) for x in mask]
    nmask = len(hex_mask)

    # start decrypt routine
    unscrambled = list(decdata[0:8])  # take unscramble header

    for i, j in zip(range(0, ndecdata - 8), cycle(range(0, nmask))):
        unscrambled = unscrambled + [decdata[i + 8] ^ int(hex_mask[j], 16)]

    result_string = "".join("{:02x}".format(n) for n in unscrambled)

    print("\t - " + "Grott - data decrypted V2")
    return result_string


def validate_record(data: bytes) -> bool:
    # validata data record on length and CRC (for "05" and "06" records)
    # The CRC is a modbus CRC
    #
    # the packet start with \x00\x0d\x00
    # Protocol byte is the fourth, ex: \x05 \x06
    # Length is the next to 2 bytes in big endian format
    # Next is data
    # The last 2 bytes if the protocol is not 2 is the CRC

    # Length of the data in bytes
    ldata = len(data)

    protocol = data[3]
    len_orgpayload = int.from_bytes(data[4:6], "big")
    print("header: {} - Data size: {}".format(to_hex(data[0:6]), ldata))
    print("\t- Protocol is: {}".format(protocol))
    print("\t- Length is: {} bytes".format(len_orgpayload))

    has_crc = False
    if protocol in (0x05, 0x06):
        has_crc = True
        # CRC is the last 2 bytes
        lcrc = 2
        crc = int.from_bytes(data[-lcrc:], "big")
    else:
        lcrc = 0

    # ldata - 6 bytes of header - crc length
    len_realpayload = (ldata - 6 - lcrc)

    if protocol != 0x02:
        crc_calc = modbus_crc(data[0:ldata - 2])
        print("Calculated CRC: {}".format(crc_calc))

    if len_realpayload == len_orgpayload:
        returncc = True
        print("Data CRC: {} - Calculated: {}".format(crc, crc_calc))
        if protocol != 0x02 and crc != crc_calc:
            return False
    else:
        returncc = False

    return returncc


def str2bool(defstr):
    if defstr in ("True", "true", "TRUE", "y", "Y", "yes", "YES", 1, "1") : defret = True
    if defstr in ("False", "false", "FALSE", "n", "N", "no", "NO", 0, "0") : defret = False
    if 'defret' in locals():
        return(defret)
    else : return()

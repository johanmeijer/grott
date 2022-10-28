# coding=utf-8

import logging
from itertools import cycle

from crc import modbus_crc

logger = logging.getLogger(__name__)


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


def validate_record(xdata):
    # validata data record on length and CRC (for "05" and "06" records)

    data = bytes.fromhex(xdata)
    ldata = len(data)
    len_orgpayload = int.from_bytes(data[4:6], "big")
    header = "".join("{:02x}".format(n) for n in data[0:8])
    protocol = header[6:8]

    if protocol in ("05", "06"):
        lcrc = 4
        crc = int.from_bytes(data[ldata - 2:ldata], "big")
    else:
        lcrc = 0

    len_realpayload = (ldata * 2 - 12 - lcrc) / 2

    if protocol != "02":
        crc_calc = modbus_crc(data[0:ldata - 2])

    if len_realpayload == len_orgpayload:
        returncc = 0
        if protocol != "02" and crc != crc_calc:
            returncc = 8
    else:
        returncc = 8

    return (returncc)


def str2bool(defstr):
    if defstr in ("True", "true", "TRUE", "y", "Y", "yes", "YES", 1, "1") : defret = True
    if defstr in ("False", "false", "FALSE", "n", "N", "no", "NO", 0, "0") : defret = False
    if 'defret' in locals():
        return(defret)
    else : return()

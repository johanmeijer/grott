# coding=utf-8

from __future__ import (absolute_import, division,
                        print_function, unicode_literals)
from builtins import *

import logging

from grottconf import Conf
from grottdata import procdata, detect_layout
from utils import validate_record

logger = logging.getLogger(__name__)

import unittest

import pytest

class TestMessageProcessing(unittest.TestCase):
    def setUp(self) -> None:
        self.raw_data = b"\x02\x2e\x00\x06\x03\x3f\x01\x04\x0d\x22\x2c\x40\x20\x47\x44\x74\x2a\x2e\x77\
\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\
\x21\x20\x22\x3b\x35\x73\x46\x5f\x47\x59\x74\x74\x47\x72\x6f\x77\x61\x74\x74\
\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x77\x7e\x69\x4b\x53\x7a\x74\x61\
\x74\x74\x3b\x72\x6a\x77\x61\x3d\xa0\x49\xeb\x6e\x8d\x61\x74\x3d\xae\x72\x6f\
\x77\x61\x74\x74\x47\x72\x6f\x76\x21\x74\x71\x9c\x70\xd2\x7f\xfb\x74\xba\x47\
\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\
\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x3f\
\xa4\x67\xf8\x4e\x49\x6f\x27\x61\x74\x3d\x60\x72\x6f\x77\x61\x74\x74\x47\x72\
\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x52\x74\
\x47\x93\xb4\x73\x09\x36\x86\x47\x72\x6f\x5f\x61\x74\x92\xbb\x72\x6f\x77\x61\
\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\
\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\
\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x90\x86\x75\
\x3e\x46\x54\x6e\x3d\x61\x74\x74\xfd\x7c\xfc\x79\xca\x74\x74\x47\x72\x6f\x77\
\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\
\x6f\x77\x61\x74\x74\x46\x1d\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\
\x47\x72\x6f\x77\x61\x74\x77\xaf\x76\x0b\x77\x64\x74\x74\x47\x72\x6f\x77\x61\
\x70\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\xd5\
\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\
\x72\x42\xc3\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x6a\xc6\x6f\x77\x7a\xc8\
\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x74\xcb\x61\x74\x74\x53\x72\x6e\x70\
\x65\x74\x74\x47\x72\x6f\x45\x61\x74\x0a\x4c\x72\x6f\x77\x6e\x74\x74\xdf\x3a\
\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\
\x0c\x72\x6f\xba\xcb\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\
\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\
\x77\x62\x9c\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\
\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\
\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\
\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\
\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x76\x0a\x73\x80\x74\x74\
\x47\x72\x6e\x18\x61\x74\x74\x47\x71\x95\x77\x61\x74\x74\x47\x72\x6f\x77\x61\
\x74\x74\x47\x72\x6f\x77\x49\x74\x74\xa2\x94\x6f\x77\x61\x6d\x74\x47\x3d\x4b\
\x77\x61\x3d\x04\x47\x72\x72\x3b\x61\x74\x74\x6f\x72\x6f\x77\x61\x74\x74\x47\
\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\
\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\
\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\
\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\
\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x46\x72\x6f\x77\x61\
\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\
\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\
\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\
\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\
\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\
\x6f\x95\x12"

        self.decoded = "000d0006033f01504a50433741333033584100000000000000000000000000000000000000004\
e57434f4134343030380000000000000000000000000000000000000000160a1c003838030000\
007c000000000000000000000000000000000000000000000000400005d902c0089a00cf00000\
00000000000000000000000000000000000000000000000000000000000000000000000000013\
8a093100090000000000000000000000000000000000000000000000000000000000000000e13\
704645ae8000000000000e6540000000000000000000000000000000000000000000000000000\
0000000000000000000000000000000000000000000000000000000000000000e73f00ec00e20\
0e4000000b9009c005b0000000000000000000000000000000000000000000000000000000000\
00016e00000003000000000000000000000000000003e80464000000000000000000040020000\
000000000000000000000000000b9000000000f3c000000000000000000000f3c000000000000\
0000000000000000000000000f3c000000000000000000000f3c0000001400000002000000000\
00500007d8400000000000097fd00000000000000000000000000000000000000050000ccc600\
00000000000000000000000000000000000000000000000000000000000000000003e80000000\
00000000000000000000000000000000000000000000000000000000000000000000000000000\
00000000000000000000000000000000000000000000000000000000000000000000000000000\
00000000000046504e100000000016e0000000703fa0000000000000000000000000000000000\
00e53f0000000000004ec80000000000000000000000000000000000000000000000000000000\
00000000000000000000000000000000000000000000000000000000000000000000000000000\
00000000000000000000000000000000000000000000000000000000000000000000000000000\
00000000001000000000000000000000000000000000000000000000000000000000000000000\
00000000000000000000000000000000000000000000000000000000000000000000000000000\
0000000000000000000000000000000000000000000000000000000009002"

    def test_parse_decoded(self):
        conf = Conf("2.7.6")
        data = procdata(conf, self.raw_data)
        print(data)
        assert isinstance(data, dict)

    def test_check_crc(self):
        "Test if the frame validation function work"
        assert validate_record(self.raw_data), "Invalid CRC"

    def test_layout_detect(self):
        layout = detect_layout(self.raw_data)
        assert layout == "T060104X"

        # Test SPH inverter
        layout = detect_layout(self.raw_data, "SPH")
        assert layout == "T060104XSPH"

    def test_decryption(self):
        # Disabled ATM
        return
        raw_data = b'\x01\xc4\x00\x06\x03\x3f\x01\x04\x0d\x22\x2c\x40\x20\x47\x44\x74\x2a\x2e\x77\
\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\
\x21\x20\x22\x3b\x35\x73\x46\x5f\x47\x59\x74\x74\x47\x72\x6f\x77\x61\x74\x74\
\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x77\x7e\x68\x4d\x5d\x66\x74\x61\
\x74\x74\x3b\x72\x6a\x77\x61\x4e\x88\x49\xe4\x6e\xe2\x61\x74\x4f\x7e\x72\x6f\
\x77\x61\x74\x74\x47\x72\x6f\x76\x21\x74\x71\x9e\x70\xde\x7f\xfa\x74\xbb\x47\
\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\
\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x4d\
\xd8\x67\xf3\x4e\x40\x6f\x36\x61\x74\x4e\x24\x72\x6f\x77\x61\x74\x74\x47\x72\
\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x7c\x74\
\x47\x93\x50\x73\x04\x1b\x41\x47\x72\x6f\x7f\x61\x74\x92\x1b\x72\x6f\x77\x61\
\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\
\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\
\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x90\x26\x75\
\x69\x46\x70\x6e\x63\x61\x74\x74\xfd\x7c\xff\x79\xcd\x74\x74\x47\x72\x6f\x77\
\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\
\x6f\x77\x61\x74\x74\x46\x1c\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\
\x47\x72\x6f\x77\x61\x74\x77\xaf\x76\x0b\x77\x64\x74\x74\x47\x72\x6f\x77\x61\
\x70\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\xd5\
\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\
\x72\x4c\xfb\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x64\xfe\x6f\x77\x77\xdc\
\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x79\xdf\x61\x74\x74\x53\x72\x6e\x70\
\x67\x74\x74\x47\x72\x6f\x54\x61\x74\x09\xec\x72\x6f\x77\x60\x74\x74\xd0\x8c\
\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\
\x6e\x72\x6f\xbb\x92\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\
\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\
\x77\x62\x9c\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\
\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\
\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\
\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\
\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x76\x0a\x73\x80\x74\x74\
\x47\x72\x6e\x19\x61\x74\x74\x47\x71\x95\x77\x61\x74\x74\x47\x72\x6f\x77\x61\
\x74\x74\x47\x72\x6f\x77\x66\x74\x74\xa2\x34\x6f\x77\x61\x72\x74\x47\x3c\xa1\
\x77\x61\x4e\x88\x47\x72\x79\xdf\x61\x74\x74\x40\x72\x6f\x77\x61\x74\x74\x47\
\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\
\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\
\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\
\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\
\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x46\x72\x6f\x77\x61\
\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\
\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\
\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\
\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\
\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\
\x6f\xa5\x2a'
        expected = "01c20006033f01044a50433741333033584100000000000000000000000000000000000000004\
e57434f4134343030380000000000000000000000000000000000000000160a1c0a2d09030000\
007c000500002c240f20012400002c3200000000000000000001400005d902b0089900cf00000\
000000000000000000000000000000000000000000000000000000000000000000000002c5a13\
8a0934003100002c4800000000000000000000000000000000000000000000000000070000e13\
e04656e3e000000070000e65b0000000000000000000000000000000000000000000000000000\
0000000000000000000000000000000000000000000000000000000000000000e746011a01020\
110000000ba0f1b0f340000000000000000000000000000000000000000000000000000000000\
00016e00000000000000000000000000000000000003e80464000500000000000000040000000\
000000000000000000000000000ba0000000000000000000000000000000000000000170c0000\
0000000000000000170c000016a80000000000000000000016a80000001400010705000000000\
02300007dab00000001000097fe00000000000000000000000000000000000000290000ccf300\
00000000000000000000000000000000000000000000000000000000000000000003e80000000\
00000000000000000000000000000000000000000000000000000000000000000000000000000\
00000000000000000000000000000000000000000000000000000000000000000000000000000\
00000000000046504e100000000016e0000000003fa0000000000000000000000000000000700\
00e5460000000600004ece00002db40000157c000000070000000000000000000000000000000\
00000000000000000000000000000000000000000000000000000000000000000000000000000\
00000000000000000000000000000000000000000000000000000000000000000000000000000\
00000000001000000000000000000000000000000000000000000000000000000000000000000\
00000000000000000000000000000000000000000000000000000000000000000000000000000\
000000000000000000000000000000000000000000000000000000000366f"
        from grottdata import decrypt
        assert decrypt(raw_data) == expected



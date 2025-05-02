import unittest
import grottproxy


# Unit Tests for modul grottproxy.py


class TestGrottProxy(unittest.TestCase):

    def test_calc_crc_with_zero_data(self):
        testvalue = ""
        self.assertEqual(grottproxy.calc_crc(testvalue), 65535)
        

    def test_calc_crc_with_some_4byte_values(self):
        test_value = bytearray(b'\xa2\x00\x00\x00\x00')
        self.assertEqual(grottproxy.calc_crc(test_value), 55773)

        test_value = bytearray(b'\xa2\x01\x02\x03\x04')
        self.assertEqual(grottproxy.calc_crc(test_value), 54908)

        test_value = bytearray(b'\xa2\xFF\xFF\xFF\x0FF')
        self.assertEqual(grottproxy.calc_crc(test_value), 27529)
        
    def test_calc_crc_with_longer_value(self):
        test_value = b'\x00\x0f\x00\x06\x01\x41\x01\x38\x1f\x35\x2b\x41\x22\x32\x40 \
        \x75\x25\x59\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61 \
        \x74\x74\x47\x72\x24\x39\x2f\x44\x30\x70\x46\x5f\x44\x23\x74\x74\x47\x72\x6f \
        \x77\x61\x74\x74\x47\x72\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x78\x70\x65 \
        \x56\x48\x71\x74\x72\xac\x67\xb8\x72\x6c\x14\x05\x74\x10\x45\x65\x90\x88\x9e \
        \x8f\x74\x47\x73\x01\x7a\x72\x79\x78\x46\x58\x6e\x63\x61\x74\x76\x61\x72\x6e \
        \x74\x81\x55\x17\x47\x72\x6d\xc8\x61\x76\x74\x47\x73\xfd\x77\x61\x74\x74\x47 \
        \x73\x2f\x27\x62\x9c\x67\xc9\x72\x67\x77\x64\x74\x7f\x47\x72\x6f\x77\x61\x74 \
        \x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x75\x74\x60\x60\x72\x6c\x14 \
        \x05\x74\x10\x45\x64\x6f\x77\x61\x74\x74\x47\x73\x0e\x7a\x70\x79\x7f\x46\x53 \
        \x6e\x71\x61\x74\x76\x61\x72\x6e\x74\x80\x56\x17\x47\x72\x6d\xc8\x61\x76\x74 \
        \x47\x73\xe5\x77\x61\x74\x74\x47\x73\x53\x1f\x62\x9c\x67\xcb\x72\x67\x77\x64 \
        \x74\x7f\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f\x77\x61\x74\x74\x47\x72\x6f \
        \x77\x75\x5c\x60\x08\x72\x6c\x14\x05\x74\x10\x45\x64\x90\x88\x9e\x8f\x74\x47 \
        \x73\x07\x7a\x71\x79\x7f\x46\x7c\x6f\x81\x61\x74\x76\x61\x72\x6e\x74\xbf\x57 \
        \x17\x47\x72\x6d\xc8\x61\x76\x74\x47\x73\xff\x77\x61\x74\x74\x47\x73\x2f\x27 \
        \x62\x9c\x67\xc8\x72\x67\x77\x64\x74\x7f\x47\x72\x6f\x77\x61\x74\x74\x47\x72 \
        \x6f\x77\x61\x74\x74\x47\x72\x6f\x77\xc9\xc4'
        self.assertEqual(grottproxy.calc_crc(test_value), 10721)
        
        
    def test_validate_record_msg_02_wrong_length(self):
        data_in_bytes  =  b'\x00=\x00\x02\x00 \x00\x16\x1f5+A"2@u%YwattGrowattGrowattGr\xe3\xfd'
        data_as_string = "".join("{:02x}".format(n) for n in data_in_bytes)
        self.assertEqual(grottproxy.validate_record(data_as_string), (8, 'data record length error')) 
        
        
    def test_validate_record_correct_msg_02(self):
        data_in_bytes  =  b'\x00=\x00\x02\x00 \x00\x16\x1f5+A"2@u%YwattGrowattGrowattGr'
        data_as_string = "".join("{:02x}".format(n) for n in data_in_bytes)
        self.assertEqual(grottproxy.validate_record(data_as_string), (0, 'ok')) 
        
        
    def test_validate_record_correct_msg_05(self):
        data_in_bytes  =  b'\x00=\x00\x05\x00 \x00\x16\x1f5+A"2@u%YwattGrowattGrowattGr\x4f\x8b'
        data_as_string = "".join("{:02x}".format(n) for n in data_in_bytes)
        self.assertEqual(grottproxy.validate_record(data_as_string), (0, 'ok')) 
        
        
    def test_validate_record_correct_msg_06(self):
        data_in_bytes  =  b'\x00=\x00\x06\x00 \x01\x16\x1f5+A"2@u%YwattGrowattGrowattGr\xe3\xfd'
        data_as_string = "".join("{:02x}".format(n) for n in data_in_bytes)
        self.assertEqual(grottproxy.validate_record(data_as_string), (0, "ok")) 
        
        
    def test_validate_record_wrong_crc(self):
        data_in_bytes  =  b'\x00=\x00\x06\x00 \x01\x16\x1f5+A"2@u%YwattGrowattGrowattGr\xe3\xff'
        data_as_string = "".join("{:02x}".format(n) for n in data_in_bytes)
        self.assertEqual(grottproxy.validate_record(data_as_string), (8, 'data record crc error')) 
        
        
    # \todo more tests should be added to test all modules of the grottproxy.py file
        
        
if __name__ == '__main__':
    unittest.main()
import unittest
import grottdata
import grottconf


# Unit Tests for modul grottdata.py



class TestGrottdataStr2Bool(unittest.TestCase):
    
    def test_str2bool(self):
        self.assertEqual(grottdata.str2bool("TRUE"), True)
        self.assertEqual(grottdata.str2bool("TRuE"), True)
        self.assertEqual(grottdata.str2bool("true"), True)
        self.assertEqual(grottdata.str2bool("True"), True)
        self.assertEqual(grottdata.str2bool("YES"),  True)
        self.assertEqual(grottdata.str2bool("Yes"),  True)
        self.assertEqual(grottdata.str2bool("yes"),  True)
        self.assertEqual(grottdata.str2bool("Y"),    True)
        self.assertEqual(grottdata.str2bool("y"),    True)
        self.assertEqual(grottdata.str2bool("1"),    True)
        self.assertEqual(grottdata.str2bool(1),      True)
        self.assertEqual(grottdata.str2bool(2),      True)
        self.assertEqual(grottdata.str2bool(123456), True)
        self.assertEqual(grottdata.str2bool(-1),     True)
        self.assertEqual(grottdata.str2bool(True),   True)
        
        self.assertEqual(grottdata.str2bool("FALSE"), False)
        self.assertEqual(grottdata.str2bool("FAlsE"), False)
        self.assertEqual(grottdata.str2bool("false"), False)
        self.assertEqual(grottdata.str2bool("False"), False)
        self.assertEqual(grottdata.str2bool("NO"),    False)
        self.assertEqual(grottdata.str2bool("No"),    False)
        self.assertEqual(grottdata.str2bool("no"),    False)
        self.assertEqual(grottdata.str2bool("N"),     False)
        self.assertEqual(grottdata.str2bool("n"),     False)
        self.assertEqual(grottdata.str2bool("0"),     False)
        self.assertEqual(grottdata.str2bool(0),       False)
        self.assertEqual(grottdata.str2bool(False),   False)
    
        self.assertEqual(grottdata.str2bool(""),      None)
        self.assertEqual(grottdata.str2bool("a"),     None)
        self.assertEqual(grottdata.str2bool("2"),     None) # should the be considered True?
        self.assertEqual(grottdata.str2bool("123"),   None) # should the be considered True?
        self.assertEqual(grottdata.str2bool("?"),     None)
        self.assertEqual(grottdata.str2bool("hello"), None)
        self.assertEqual(grottdata.str2bool("ABC"),   None)
        self.assertEqual(grottdata.str2bool("!&/("),  None)


class TestGrottPVOutputLimit(unittest.TestCase):

    def test_ok_send_run_once_should_be_ok(self):
        defined_key = {}
        defined_key["pvserial"] = "1234"
        conf   = grottconf.Conf("3.0.0_20241208")
        pvout_limit = grottdata.GrottPvOutLimit()
        result = pvout_limit.ok_send(defined_key["pvserial"], conf)
        self.assertEqual(result, True)
        
        
    def test_ok_send_run_twice_should_not_be_ok(self):
        defined_key = {}
        defined_key["pvserial"] = "1234"
        conf   = grottconf.Conf("3.0.0_20241208")
        pvout_limit = grottdata.GrottPvOutLimit()
        result1 = pvout_limit.ok_send(defined_key["pvserial"], conf)
        result2 = pvout_limit.ok_send(defined_key["pvserial"], conf)
        self.assertEqual(result1, True)
        self.assertEqual(result2, False)


    def test_format_multi_line_string_shorter_than_limit(self):
        data = "abc"
        result = grottdata.format_multi_line("", data, 4)
        self.assertEqual(result, "abc")


    def test_format_multi_line_string_length_equal_to_limit(self):
        data = "123"
        result = grottdata.format_multi_line("", data, 3)
        self.assertEqual(result, "123")


    def test_format_multi_line_string_length_longer_to_limit(self):
        data = "---"
        result = grottdata.format_multi_line("", data, 2)
        self.assertEqual(result, "--\n-")


    def test_format_multi_line_string_add_prefix(self):
        data = "123"
        result = grottdata.format_multi_line("###", data, 12)
        self.assertEqual(result, "###123")
        
        
            
    def test_AutoCreateLayout_short_data_protocol_0(self):
        conf       = grottconf.Conf("3.0.0_20241208")
        data       = bytes(b'abcdef')
        protocol   = 0
        deviceno   = 1
        recordtype = 3
        result     = grottdata.AutoCreateLayout(conf, data, protocol, deviceno, recordtype)
        expected_result = ("none", '616263646566')
        self.assertEqual(result, expected_result)


    def test_AutoCreateLayout_short_data_protocol_02(self):
        conf       = grottconf.Conf("3.0.0_20241208")
        data       = bytes(b'xyz')
        protocol   = '02'
        deviceno   = 1
        recordtype = 3
        result     = grottdata.AutoCreateLayout(conf, data, protocol, deviceno, recordtype)
        expected_result = ("none", '78797a')
        self.assertEqual(result, expected_result)

    
    def test_AutoCreateLayout_short_data_protocol_05(self):
        conf       = grottconf.Conf("3.0.0_20241208")
        data       = bytes(b'xyz')
        protocol   = '05'
        deviceno   = '01'
        recordtype = '03'
        result     = grottdata.AutoCreateLayout(conf, data, protocol, deviceno, recordtype)
        expected_result = ("none", '78797a')
        self.assertEqual(result, expected_result)
    
    
    def test_AutoCreateLayout_short_data_protocol_06(self):
        conf       = grottconf.Conf("3.0.0_20241208")
        data       = bytes(b'a')
        protocol   = '06'
        deviceno   = '01'
        recordtype = '03'
        result     = grottdata.AutoCreateLayout(conf, data, protocol, deviceno, recordtype)
        expected_result = ("none", '61')
        self.assertEqual(result, expected_result)
        
    
    def test_AutoCreateLayout_correct_data_unknown_layout_T060103(self):
        conf       = grottconf.Conf("3.0.0_20241208")
        data       = bytes(b'abcdefgahcdefgh')
        protocol   = '06'
        deviceno   = '01'
        recordtype = '03'
        result     = grottdata.AutoCreateLayout(conf, data, protocol, deviceno, recordtype)
        expected_result = ("T060103", '61626364656667612f110b1207131c')
        self.assertEqual(result, expected_result)
        

    def test_procdata(self):
        result   = 1
        expected = 1
        self.assertEqual(result, expected)


class TestDecrypt(unittest.TestCase):
    
    # Datastreams with length smaller than 9 bytes are not encrypted
    def test_decrypt_data_smaller_than_9byte(self):
        data_bin = b'\x00'
        expected = "00"
        result   = grottdata.decrypt(data_bin)
        self.assertEqual(result, expected)
        
        data_bin = b'\xff'
        expected = "ff"
        result   = grottdata.decrypt(data_bin)
        self.assertEqual(result, expected)
        
        data_bin = b'\x1e\x7a'
        expected = "1e7a"
        result   = grottdata.decrypt(data_bin)
        self.assertEqual(result, expected)
        
        data_bin = b'\x00\x00\x00\x00'
        expected = "00000000"
        result   = grottdata.decrypt(data_bin)
        self.assertEqual(result, expected)

        data_bin = b'\x01\x02\x03\x04\x05\x06\x07'
        expected = "01020304050607"
        result   = grottdata.decrypt(data_bin)
        self.assertEqual(result, expected)
        
        data_bin = b'\x01\x02\x03\x04\x05\x06\x07\x08'
        expected = "0102030405060708"
        result   = grottdata.decrypt(data_bin)
        self.assertEqual(result, expected)


    # The first 8 bytes of a datastreams are not encrypted. 
    # Messages longer than 8 bytes are decrypted starting at byte 9
    def test_decrypt_data_9bytes_long_and_longer(self):
        data_bin = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09'
        expected = "01020304050607084e"
        result   = grottdata.decrypt(data_bin)
        self.assertEqual(result, expected)
        
        data_bin = b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
        expected = "00010203040506074f7b657c6d797a48"
        result   = grottdata.decrypt(data_bin)
        self.assertEqual(result, expected)
        
        data_bin = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        expected = "000000000000000047726f7761747447"
        result   = grottdata.decrypt(data_bin)
        self.assertEqual(result, expected)

        data_bin = b'\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x04\x08\x10\x20\x30\x40'
        expected = "000000000000000046706b7f71544407"
        result   = grottdata.decrypt(data_bin)
        self.assertEqual(result, expected)
        
        data_bin = b'\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x04\x08\x10\x20\x30\x40\x08\x01\x02\x03\x04\10\x20\x40'
        expected = "000000000000000046706b7f715444077a6e7562707c6732"
        result   = grottdata.decrypt(data_bin)
        self.assertEqual(result, expected)

        data_bin = b'\x00\x01\x02\x03\x04\x05Growatt'
        expected = "000102030405477228050e0315"
        result   = grottdata.decrypt(data_bin)
        self.assertEqual(result, expected)
        
        
    # \todo: for every protocol grott supports a message should be added to the test
    def test_decrypt_with_real_data_message(self):
        data_bin = b'' # \todo fill in a real data message
        expected = ""  # \todo fill in the expected result for the changed data message
        result   = grottdata.decrypt(data_bin)
        self.assertEqual(result, expected)
        

if __name__ == '__main__':
    unittest.main()
import unittest
import grottdata


# Unit Tests for modul grottdata.py


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
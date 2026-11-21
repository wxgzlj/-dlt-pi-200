import unittest
from generate_forecast import HashStream, map_window, sample_without_replacement, weighted_without_replacement

class TestGenerator(unittest.TestCase):
    def test_hash_stream_reproducible(self):
        a=HashStream(bytes.fromhex("11"*32))
        b=HashStream(bytes.fromhex("11"*32))
        self.assertEqual([a.randbelow(37) for _ in range(100)],[b.randbelow(37) for _ in range(100)])

    def test_randbelow_range(self):
        r=HashStream(bytes.fromhex("22"*32))
        for n in (1,2,3,12,35,1000,2**32+15):
            for _ in range(100):
                self.assertTrue(0 <= r.randbelow(n) < n)

    def test_pi_maps_are_valid(self):
        w="31415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679"
        w=(w*30)[:2048]
        for mode in ("identity","reverse","complement9"):
            f,_=map_window(w,35,5,mode)
            b,_=map_window(w,12,2,mode)
            self.assertEqual(len(set(f)),5)
            self.assertEqual(len(set(b)),2)
            self.assertTrue(all(1<=x<=35 for x in f))
            self.assertTrue(all(1<=x<=12 for x in b))

    def test_sampling_without_replacement(self):
        r=HashStream(bytes.fromhex("33"*32))
        self.assertEqual(len(set(sample_without_replacement(list(range(1,36)),5,r))),5)
        self.assertEqual(len(set(weighted_without_replacement({i:i for i in range(1,36)},35,5,r))),5)

if __name__=="__main__":
    unittest.main()

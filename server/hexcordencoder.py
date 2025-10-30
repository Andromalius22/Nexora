import msgpack

# Example: ExtType code for HexCoord, must be 0–127
HEX_COORD_EXT = 1

class HexCoord:
    def __init__(self, q, r, s):
        self.q = q
        self.r = r
        self.s = s

    def pack(self):
        # Pack three 32-bit integers → 12 bytes
        return self.q.to_bytes(4, 'big', signed=True) + \
               self.r.to_bytes(4, 'big', signed=True) + \
               self.s.to_bytes(4, 'big', signed=True)

    @classmethod
    def unpack(cls, data):
        q = int.from_bytes(data[0:4], 'big', signed=True)
        r = int.from_bytes(data[4:8], 'big', signed=True)
        s = int.from_bytes(data[8:12], 'big', signed=True)
        return cls(q, r, s)

# Packer and Unpacker hooks
def ext_encoder(obj):
    if isinstance(obj, HexCoord):
        return msgpack.ExtType(HEX_COORD_EXT, obj.pack())
    return obj

def ext_decoder(code, data):
    """
    MsgPack ext_hook for decoding custom types.
    """
    if code == HEX_COORD_EXT:
        return HexCoord.unpack(data)
    return msgpack.ExtType(code, data)

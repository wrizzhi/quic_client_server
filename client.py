import random,itertools,struct
import ParserClient
from QUIC_Client import quicconnectclient
import time
import sys



def randbytes(n,_struct8k=struct.Struct("!1000Q").pack_into):
    if n<8000:
        longs=(n+7)//8
        return struct.pack("!%iQ"%longs,*map(
            random.getrandbits,itertools.repeat(64,longs)))[:n]
    data=bytearray(n);
    for offset in range(0,n-7999,8000):
        _struct8k(data,offset,
            *map(random.getrandbits,itertools.repeat(64,1000)))
    offset+=8000
    data[offset:]=randbytes(n-offset)
    return data


def main():
    print("started")
    args = ParserClient.parse("Parse client args")
    test_data = []
    for i in range(0,110):
        q = randbytes(n=100000)
        test_data.append(q)
    print(sys.getsizeof(test_data[0]))
    k = quicconnectclient(args.host,args.port,args.verbose)
      
    for i in test_data:   
        #print(i)

        k.quic_obj.send_frame(i)
        time.sleep(0.03)

    #k.quic_obj.client_close()

if __name__ == "__main__":
    main()

import random,itertools,struct
from timeit import default_timer as timer
 

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
    q = randbytes(n=50000)
    start = timer()
    info = [q[i:i+950] for i in range(0, len(q), 950)]
    end = timer()
    print(f'elapsed time: {end - start}')
    print(len(info))


if __name__ == '__main__':
    main()
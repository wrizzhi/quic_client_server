import logging
import queue
import ssl
import asyncio
import sys
import time
from typing import Optional, cast
import threading
import random,itertools,struct
from aioquic.asyncio import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio.client import connect
from aioquic.quic.events import QuicEvent, StreamDataReceived
from timeit import default_timer as timer

import ParserClient
from quic_logger import QuicDirectoryLogger

logger = logging.getLogger("client")

# Globals for throughput calculation
input_data = queue.Queue()
total_bytes = 0
id = -1
start = 0
end = 0
dd = 0
# Define how the client should work. Inherits from QuicConnectionProtocol.
# Override QuicEvent


class MyClient(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ack_waiter: Optional[asyncio.Future[None]] = None
        self.offset = 0
    
    def insert_timestamp(self,data,index):
        #inserting the offset and send time
        self.t1 =  time.time()
        header = str(self.t1) +  "," + str(self.offset) + "," + str(index) + ","
        header = header.encode()
        data = header + data
        return data

    # Assemble a query to send to the server
    async def query(self,data,index) -> None:
        #print("ct",ct)
        query = data
        if isinstance(query,str):
            query = query.encode()
        stream_id = self._quic.get_next_available_stream_id()   
        logger.debug(f"Stream ID: {stream_id}")
        
        global start
        start = time.time()
        # Send the query to the server
        query = self.insert_timestamp(query,index)
        #total_bytes = sys.getsizeof(bytes(query))
        #print("TOTAL BYTES: " + str(total_bytes))
        self._quic.send_stream_data(stream_id, bytes(query), True)
        waiter = self._loop.create_future()
        self._ack_waiter = waiter
        self.transmit()
        return await asyncio.shield(waiter)

    # Define behavior when receiving a response from the server
    def quic_event_received(self, event: QuicEvent) -> None:
        if self._ack_waiter is not None:
            if isinstance(event, StreamDataReceived):
                t4 = time.time()
                # get timestamp in seconds and convert to MS
                global end,dd
                end = time.time()
                #print("reply",event.data.decode())
                dd+=1
                if ( dd == 1):
                    answer = event.data.decode()
                    t2,t3,rest = answer.split(",",2)
                    #print("t2",t2)
                    #print("t3",t3)
                    #print("rest",rest)
                    mpd = ((float(t2)- float(self.t1)) + (t4 - float(t3)))/2
                    self.offset = (float(t2)- float(self.t1)) - mpd
                    #print("offset",self.offset)


                # calculate throughput and write to file
                #python QUIC_Client.py -k -qsize 50000 -v
                # convert bytes to bits, then to megabits to measure in megabits per second
                total_time = end - start
                total_bits = (total_bytes * 8) / 1e+6
                throughput = total_bits / total_time

            

              
                
                #print(answer.decode())
                waiter = self._ack_waiter
                if event.end_stream:
                    dd = 0
                    self._ack_waiter = None
                    waiter.set_result(None)
#                    print("end of received")




class quicconnect(MyClient):
    def __init__(self, host_addr, port_nr,configuration):
        super().__init__(self)
        self.host_addr = host_addr
        self.port_nr = port_nr
        self.configuration =configuration
        self.frame_hist = list()
        self.start_thread()
    

    def send_thread(self):
            asyncio.run(self.run())

    def start_thread(self):
            self.x = threading.Thread(target=self.send_thread)
            self.x.start()
    
    def send_frame(self,frame):
        self.frame_hist.append(frame)

            
            

    async def run(self):
            async with connect(
            self.host_addr,
            self.port_nr,
            configuration=self.configuration,
            create_protocol=MyClient,
             ) as client:
              self.client = cast(MyClient, client)
              while True:
                  global id 
                  if (len(self.frame_hist) > 0):  
                        curr_time = time.time()
                        id +=1
                        data = self.frame_hist.pop(0)
                        await self.client.query(data,id)  
                  else:
                      if (time.time() - curr_time > 2 ):
                          print("Timeout")
                          break
                      
                          

            #self.client.close()  
              


class quicconnectclient():
    def __init__(self, host_addr, port_nr,verbose):
            logging.basicConfig(
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            level=logging.DEBUG if verbose else logging.INFO,)
            self.configuration = QuicConfiguration(is_client=True) 
            self.configuration.verify_mode = ssl.CERT_NONE
            self.hostip = host_addr
            self.portnr = port_nr
            self.quic_obj = self.create_quic_server_object()
    
    def create_quic_server_object(self):
            return   quicconnect(self.hostip,self.portnr,configuration=self.configuration)



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
    for i in range(0,20):
        q = randbytes(n=50000)
        test_data.append(q)
    global _args
    _args = args
    k = quicconnectclient(args.host,args.port,args.verbose)
      
    for i in test_data:   
        k.quic_obj.send_frame(i)
        time.sleep(0.03)

if __name__ == "__main__":
    main()

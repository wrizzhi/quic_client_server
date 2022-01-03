import logging
import ssl
import asyncio
import time
from typing import Optional, cast
import threading
import random,itertools,struct
from aioquic.asyncio import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.asyncio.client import connect
from aioquic.quic.events import QuicEvent, StreamDataReceived

import ParserClient
from quic_logger import QuicDirectoryLogger

logger = logging.getLogger("client")

id = 0
dd = 0
server_reply = list()
# Define how the client should work. Inherits from QuicConnectionProtocol.
# Override QuicEvent


class MyClient(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ack_waiter: Optional[asyncio.Future[None]] = None
        self.offset = 0
    
    def insert_timestamp(self,data,index):
        #inserting the offset,send time,index
        self.t1 =  time.time()
        header = str(self.t1) +  "," + str(self.offset) + "," + str(index) + ","
        header = header.encode()
        data = header + data
        return data

    # Assemble a query to send to the server
    async def query(self,data,index) -> None:
        
        query = data
        if isinstance(query,str):
            query = query.encode()
        stream_id = self._quic.get_next_available_stream_id()   
        logger.debug(f"Stream ID: {stream_id}")
        query = self.insert_timestamp(query,index)
        self._quic.send_stream_data(stream_id, bytes(query), True)
        waiter = self._loop.create_future()
        self._ack_waiter = waiter
        self.transmit()
        return await asyncio.shield(waiter)

    # Define behavior when receiving a response from the server
    def quic_event_received(self, event: QuicEvent) -> None:
        if self._ack_waiter is not None:
            if isinstance(event, StreamDataReceived):
                global dd,server_reply
                t4 = time.time()
                dd+=1
                waiter = self._ack_waiter
                if event.end_stream:
                    dd = 0
                    data = event.data
                    #print(data.decode())
                    self._ack_waiter = None
                    waiter.set_result(None)
                elif ( dd == 1):
                    answer = event.data.decode()
                    t2,t3 = answer.split(",",2)
                    mpd = ((float(t2)- float(self.t1)) + (t4 - float(t3)))/2
                    self.offset = (float(t2)- float(self.t1)) - mpd
                else:
                    reply = event.data.decode()
                    server_reply.append(reply)
                    print(reply)
                #python QUIC_Client.py -k -qsize 50000 -v

                





class quicconnect(MyClient):
    def __init__(self, host_addr, port_nr,configuration):
        super().__init__(self)
        self.host_addr = host_addr
        self.port_nr = port_nr
        self.configuration =configuration
        self.frame_hist = list()
        self.closed = False
        self.start_thread()
    

    def send_thread(self):
            asyncio.run(self.run())

    def start_thread(self):
            self.x = threading.Thread(target=self.send_thread)
            self.x.start()
    
    def send_frame(self,frame):
        self.frame_hist.append(frame)
    
    def client_close(self):
        self.closed = True
         
            

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
                          print("Timeout ")
                          break
                      elif(self.closed):
                          print("Client Closed")
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




import ParserServer
import asyncio
import logging
import ssl
import time
from queue import Queue
import threading
from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection
from aioquic.quic.events import QuicEvent, StreamDataReceived
from typing import Counter, Optional

from quic_logger import QuicDirectoryLogger

logger = logging.getLogger("server")
dd = 0
total_data = bytes()
frame_data = []
send_time = 0
t2 = 0
offset = 0 
index = 0
server_send_data = []



class MyConnection:
    def __init__(self, quic: QuicConnection):
        self._quic = quic

    
    def handle_event(self, event: QuicEvent) -> None:
        global total_data,dd,send_time,t2,offset,index,server_send_data
        
        if isinstance(event, StreamDataReceived):
            data = event.data
            dd +=1
            if event.end_stream:
                dd = 0
                time_taken = float(t2) - float(send_time) + float(offset)
                if time_taken < 0:
                    print("here")
                    time_taken = float(t2) - float(send_time)
                total_data += data
                temp = dict()
                temp["data"] = total_data
                temp["id"] = index
                temp["time_taken"] = time_taken
                frame_data.append(temp)
                total_data = bytes()
                ack = "frame " + str(index) + " recieved"
                self._quic.send_stream_data(event.stream_id, bytes(ack.encode()), True)
            elif  ( dd == 1):
                send_time,offset,index,data=data.decode('latin-1').split(",",3)
                t2 = str(time.time())
                data = data.encode()
                t3 = str(time.time())
                ts_data = t2 + "," + t3 
                ts_data = ts_data.encode()
                self._quic.send_stream_data(event.stream_id, ts_data, False)
                total_data += data
            else:
                if (len(server_send_data) > 0 ):
                    sever_reply = server_send_data.pop(0)
                    if isinstance(sever_reply,str):
                        sever_reply = sever_reply.encode()
                    self._quic.send_stream_data(event.stream_id, sever_reply, False)
         
                
            
            
   


class MyServerProtocol(QuicConnectionProtocol):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._myConn: Optional[MyConnection] = None
        

    def quic_event_received(self, event: QuicEvent) -> None:

        #print("receieved a connection")
        #python QUIC_Server.py -c keys/RootCA.crt -k keys/RootCA.key
        self._myConn = MyConnection(self._quic)
        self._myConn.handle_event(event)

class quicserver(MyServerProtocol):
    def __init__(self, host, port, configuration):
        super().__init__(self)
        self.host = host
        self.port = port
        self.config = configuration
        self.server_start()

    
    def recieve(self):
        t1 = time.time()
        while True and (time.time() - t1) < 2 :
            if (len(frame_data) > 0 ):
                t1 = time.time()
                temp = frame_data.pop(0)
                frame_ret = temp["data"]
                frame_time = temp["time_taken"]
                frame_index = temp["id"]
                return frame_index,frame_ret,frame_time
        return None,None,None
        
    def server_start(self):
        self.y = threading.Thread(target=self.quicrecieve)
        
        self.y.start()

    def server_send(self,data):
        global server_send_data
        server_send_data.append(data)

        

    def quicrecieve(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
        serve(
            self.host,
            self.port,
            configuration=self.config,
            create_protocol=MyServerProtocol
            )
        )
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            exit()
            pass

class quicconnectserver():
    def __init__(self, host, port,certificate,private_key,verbose,qlog=None):
            logging.basicConfig(
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            level=logging.DEBUG if verbose else logging.INFO,)
            if qlog:
                self.configuration = QuicConfiguration(is_client=False, quic_logger=QuicDirectoryLogger(qlog)) 
            else:
                self.configuration = QuicConfiguration(is_client=False, quic_logger=None) 
            self.configuration.load_cert_chain(certificate, private_key)
            self.configuration.verify_mode = ssl.CERT_NONE
            self.hostip = host
            self.portnr = port
            self.quic_obj = self.create_quic_server_object()
    
    def create_quic_server_object(self):
            return   quicserver(self.hostip,self.portnr,configuration=self.configuration)




def processing(server,data_queue):
    
    time_start = time.time()
    
    while True:
        if data_queue and  time.time() - time_start < 10:
            
            frame = data_queue.get()
            t2 = time.time()
        
            if ( frame["time_taken"] + (t2 - frame["t1"]) < 0.15):
                print("frame ",frame["id"]," processing")
                time.sleep(0.03)
                server_reply = frame["id"] + "processed"
                server.quic_obj.server_send(server_reply)
                time_start = time.time()
            else:
                print("frame ",frame["id"]," dropped")
                server_reply = frame["id"] + "dropped"
                server.quic_obj.server_send(server_reply)

def main():
    print("entered server code")

    
    args = ParserServer.parse("Parse server args")
    data_queue = Queue()
    j = quicconnectserver(args.host,args.port,args.certificate, args.private_key,args.verbose)
    prc_thread = threading.Thread(target=processing,args=(j,data_queue))
    prc_thread.start()
    counter = 0
    while True:
        id,f,t=j.quic_obj.recieve()
        if id:
            temp = dict()
            temp["frame"] = f
            temp["time_taken"] = t
            temp["t1"] = time.time()
            temp["id"] = id
            print("frame",id,"time",t)
            data_queue.put(temp)
            
        else:
            if counter > 10:
                exit()
            counter+=1
            
            

if __name__ == "__main__":
    main()

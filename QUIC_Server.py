import ParserServer
import asyncio, sys
import logging
import ssl
import time
import queue
from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection
from aioquic.quic.events import QuicEvent, StreamDataReceived
from typing import Counter, Optional

from quic_logger import QuicDirectoryLogger

logger = logging.getLogger("server")
dd = 0
total_data = bytes()
q= queue.Queue()
send_time = 0
t2 = 0
offset = 0 



class MyConnection:
    def __init__(self, quic: QuicConnection):
        self._quic = quic

    
    def handle_event(self, event: QuicEvent) -> None:
        global total_data,dd,send_time,t2,offset
        
        if isinstance(event, StreamDataReceived):
            data = event.data
            
           
            dd +=1
            if  ( dd == 1):
                #print("first",data.decode())
                send_time,offset,index,data=data.decode('latin-1').split(",",3)
                #print("s",send_time)
                #print("o",offset)
                print("frame",index,"recieved")
                t2 = str(time.time())
                data = data.encode()
                t3 = str(time.time())
                test = t2 +"," + t3 + "," + "hello   " + str(event.stream_id) +"\n"
                test = test.encode()
                self._quic.send_stream_data(event.stream_id, test, False)
            total_data += data
            if event.end_stream:
                dd = 0
        
                #print("END STREAM",event.stream_id)
                #logger.info("END STREAM LOGGED")
                print("final data",sys.getsizeof(total_data))
                #print("total_data",total_data)
                #print("send_time",send_time)
                print("time_taken",float(t2) - float(send_time) + float(offset))
                q.put(total_data)
                total_data = bytes()
                self._quic.send_stream_data(event.stream_id, bytes("git all".encode()), True)
   


class MyServerProtocol(QuicConnectionProtocol):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._myConn: Optional[MyConnection] = None
        

    def quic_event_received(self, event: QuicEvent) -> None:

        #print("receieved a connection")
        #python QUIC_Server.py -c keys/RootCA.crt -k keys/RootCA.key
        self._myConn = MyConnection(self._quic)
        self._myConn.handle_event(event)


def main():
    print("entered server code")

    args = ParserServer.parse("Parse server args")

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    if args.quic_log:
        quic_logger = QuicDirectoryLogger(args.quic_log)
    else:
        quic_logger = None

    configuration = QuicConfiguration(
        is_client=False, quic_logger=quic_logger
    )

    configuration.load_cert_chain(args.certificate, args.private_key)


    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        serve(
            args.host,
            args.port,
            configuration=configuration,
            create_protocol=MyServerProtocol
        )
    )

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print(q.qsize())
        pass


if __name__ == "__main__":
    main()

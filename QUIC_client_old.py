import logging
import queue
import ssl
import asyncio
import sys
import time
from typing import Optional, cast
import threading
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
id = 0
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
    
    def insert_timestamp(self,data):
        #inserting the offset and send time
        self.t1 =  time.time()
        header = str(self.t1) +  "," + str(self.offset) + ","
        header = header.encode()
        data = header + data
        return data

    # Assemble a query to send to the server
    async def query(self,ct) -> None:
        #print("ct",ct)
        query = "H" * _args.query_size
        #print("ARGS.SIZE: " + str(_args.query_size))
        #stream_id = self._quic.get_next_available_stream_id()
        query = query.encode()
        stream_id = self._quic.get_next_available_stream_id()   
        logger.debug(f"Stream ID: {stream_id}")
        # Get number of bytes to be sent to calculate throughput
        global total_bytes
        total_bytes = sys.getsizeof(bytes(query))
        #print("TOTAL BYTES: " + str(total_bytes))
        # capture start time in seconds
        global start
        start = time.time()
        # Send the query to the server
        query = self.insert_timestamp(query)
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


async def run(
    configuration: QuicConfiguration,
    host: str,
    port: int,
) -> None:
    print(f"Connecting to {host}:{port}")
    async with connect(
        host,
        port,
        configuration=configuration,
        create_protocol=MyClient,
    ) as client:
        client = cast(MyClient, client)
        logger.debug("Sending query")
        print("starting timer")
        a = time.time()
        for i in range(0,10):
            await client.query(i)
        b = time.time()
        print("returned after query")
        print(f'elapsed time: {b - a}')
        client.close()



def main():
    print("Entered client")
    

    args = ParserClient.parse("Parse client args")
    global _args
    _args = args

    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    configuration = QuicConfiguration(
        is_client=True
    )

    if args.ca_certs:
        configuration.load_verify_locations(args.ca_certs)
    if args.insecure:
        configuration.verify_mode = ssl.CERT_NONE
    if args.quic_log:
        configuration.quic_logger = QuicDirectoryLogger(args.quic_log)
    if args.secrets_log:
        configuration.secrets_log_file = open(args.secrets_log, "a")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        run(
            configuration=configuration,
            host=args.host,
            port=args.port,
        )
    )
    


if __name__ == "__main__":
    main()

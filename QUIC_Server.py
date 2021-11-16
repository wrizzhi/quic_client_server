import ParserServer
import asyncio, sys
import logging
import ssl
import queue
from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection
from aioquic.quic.events import QuicEvent, StreamDataReceived
from typing import Counter, Optional

from quic_logger import QuicDirectoryLogger

logger = logging.getLogger("server")
counter = 1
total_data = bytes()
q= queue.Queue()


class MyConnection:
    def __init__(self, quic: QuicConnection):
        self._quic = quic

    def handle_event(self, event: QuicEvent) -> None:
        global counter,total_data
        if isinstance(event, StreamDataReceived):
            data = event.data
            counter += 1
            total_data += data

            #print(data.decode())
            #print("split data",sys.getsizeof(data))
            #end_stream = True
            #print("streamid",event.stream_id)
            if event.end_stream:
                print("END STREAM",event.stream_id)
                logger.info("END STREAM LOGGED")
                print("final data",sys.getsizeof(total_data))
                q.put(total_data)
                total_data = bytes()
                self._quic.send_stream_data(event.stream_id, bytes(data), True)
    def server_reply(self):
        stream_id = self._quic.get_next_available_stream_id()


class MyServerProtocol(QuicConnectionProtocol):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._myConn: Optional[MyConnection] = None

    def quic_event_received(self, event: QuicEvent) -> None:

        #print("receieved a connection")
        self._myConn = MyConnection(self._quic)
        self._myConn.handle_event(event)

        """if isinstance(event, ProtocolNegotiated):
            if event.alpn_protocol in DnsServerProtocol.SUPPORTED_ALPNS:
                self._dns = DnsConnection(self._quic)
        if self._dns is not None:
            self._dns.handle_event(event)"""


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
        print(counter)
        for i in range((q.qsize())):
            print(i,"data")
        pass


if __name__ == "__main__":
    main()

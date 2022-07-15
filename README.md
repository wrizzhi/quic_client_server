# quic_client_server
A simple data transfer between client server using aioquic 
How to run Client and Server files

CLIENT:- python3 client.py --ca-certs aioquic/tests/pycacert.pem --host 127.0.0.1                                                                 
SERVER:- python3 server.py --certificate aioquic/tests/ssl_cert.pem --private-key aioquic/tests/ssl_key.pem -v 

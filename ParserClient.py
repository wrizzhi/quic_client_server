import argparse

def parse(name):

    parser = argparse.ArgumentParser(description="Parser for Quic Server")

    parser.add_argument("-t", "--type", type=str, help="Type of record to ")

    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="The remote peer's host name or IP address",
    )

    parser.add_argument(
        "--port", type=int, default=4784, help="The remote peer's port number"
    )

    parser.add_argument(
        "-k",
        "--insecure",
        action="store_true",
        help="do not validate server certificate",
    )

    parser.add_argument(
        "--ca-certs", type=str, help="load CA certificates from the specified file"
    )

    parser.add_argument(
        "-q",
        "--quic-log",
        type=str,
        help="log QUIC events to QLOG files in the specified directory",
    )

    parser.add_argument(
        "-l",
        "--secrets-log",
        type=str,
        help="log secrets to a file, for use with Wireshark",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="increase logging verbosity"
    )

    parser.add_argument(
        "-td",
        "--test-dir",
        type=str,
        help="directory to output throughput measurements to"
    )

    parser.add_argument(
        "-qsize",
        "--query-size",
        type=int,
        help="Amount of data to send in bytes"
    )

    args = parser.parse_args()

    return args

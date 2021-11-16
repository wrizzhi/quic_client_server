import argparse

def parse(name):

    parser = argparse.ArgumentParser(description=f"Parse args for the QUIC protocol")

    parser.add_argument(
        "--host",
        type=str,
        default="::",
        help="listen on the specified address (defaults to ::)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=4784,
        help="listen on the specified port (defaults to 4784)",
    )

    parser.add_argument(
        "-c",
        "--certificate",
        type=str,
        required=True,
        help="load the TLS certificate from the specified file",
    )

    parser.add_argument(
        "-k",
        "--private-key",
        type=str,
        help="load the TLS private key from the specified file",
    )

    parser.add_argument(
        "-q",
        "--quic-log",
        type=str,
        help="log QUIC events to QLOG files in the specified directory",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="increase logging verbosity"
    )

    args = parser.parse_args()

    return args

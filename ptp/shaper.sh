#!/bin/bash
# -*- mode: sh -*-
# Code borrowed from. https://github.com/awstream/awstream/blob/master/scripts/shaper
set -e
# set -x

# SINK=130.37.164.129 # ssh.data.vu.nl
SINK=192.168.1.4 # fs0.das5.cs.vu.nl
SOURCES=(
)

## This script wraps Linux tc to provide easy traffic shaping control.
## To use this script, do the following:
##
## ```
## $ chmod +x shaper
## $ ./shaper start <interface> <bw>
## $ ./shaper update <interface> <bw>
## $ ./shaper clear <interface>
## ```

function usage() {
    cat <<EOF
Usage:
Default shaping traffic with port 8888; configurable via env PORT

./shaper start <interface> <bw as XXX kbit>"
./shaper update <interface> <bw as XXX kbit>"
./shaper clear <interface>"
./shaper show  <interface>"

To add latency shaping, simply set environment variable LATENCY.
Example: LATENCY="100ms 10ms 25%"

EOF
}

## Creates a packet shaping pipeline:
## Packet -> Filter -> Class -> Qdisc -> Network
##
## Notice in the implementation, these components are created in the reverse
## order
##
## This function takes two arguments: `interface`, `bw`
##
## If the third argument is provided (it should also follow a `bw` spec), it's
## then used to shape another class label 1:11 (port 9999).
function shaper_start() {
    if [ $# -lt 2 ]; then
        >&2 printf "Missing interface and bandwidth specification\n\n"
        usage
        return
    fi

    tc qdisc add dev $1 root handle 1: htb
    tc class add dev $1 parent 1: classid 1:10 htb rate $2
    tc filter add dev $1 protocol ip parent 1: \
       prio 1 u32 match ip dst ${SINK} flowid 1:10

    for i in "${!SOURCES[@]}"
    do
        src="${SOURCES[$i]}"
        tc filter add dev $1 protocol ip parent 1: \
           prio 1 u32 match ip dst ${src} flowid 1:10
    done

    if [ ! -z ${LATENCY+x} ]; then
        tc qdisc add dev $1 parent 1:10 handle 10: netem delay \
           ${LATENCY}
           # ${LATENCY} distribution normal
        echo "shaping latency as '$LATENCY'";
    fi
}

## Updates the shaper option on a specific interface.
## Arguments: `interface`, `bw`
##
## If the third argument is provided (it should also follow a `bw` spec), it's
## then used to shape another class label 1:11 (port 9999).
function shaper_update() {
    tc class replace dev $1 parent 1: classid 1:10 htb rate $2
}

## Clear any shaping filters on a specific interface.
function shaper_clear() {
    tc qdisc del dev $1 root
}

## Show shaping options (qdisc, class, filter) on a specific interface.
function shaper_show() {
    tc qdisc show dev $1
    tc class show dev $1
    tc filter show dev $1
}

function main() {
    if [ $# -lt 1 ]; then
        usage;
        exit;
    fi
    command=$1
    shift
    case $command in
        show)
            shaper_show $@
            ;;
        start)
            shaper_start $@
            ;;
        update)
            shaper_update $@
            ;;
        clear)
            shaper_clear $@
            ;;
        *)
            usage
    esac
}

main $@

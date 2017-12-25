#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from threading import *
import time
import sys


BLASTER_IP = "192.168.100.1"
BLASTER_MAC = "10:00:00:00:00:01"

MIDDLEBOX_BLASTER_IP = "192.168.100.2"
MIDDLEBOX_BLASTER_MAC = "40:00:00:00:00:01"

MIDDLEBOX_BLASTEE_IP = "192.168.200.2"
MIDDLEBOX_BLASTEE_MAC = "40:00:00:00:00:02"

BLASTEE_IP = "192.168.200.1"
BLASTEE_MAC = "20:00:00:00:00:01"

net1 = None
content_array = None


def set_ip_layer(pkt):
    pkt[IPv4].src = BLASTEE_IP
    pkt[IPv4].dst = MIDDLEBOX_BLASTEE_IP
    return pkt


def set_ethernet_layer(pkt):
    pkt[Ethernet].src = BLASTEE_MAC
    pkt[Ethernet].dst = MIDDLEBOX_BLASTEE_MAC
    return pkt


def set_transport_layer(pkt):
    pkt[UDP].src = 4444
    pkt[UDP].dst = 5555
    return pkt


def add_seq_number(seq_num, pkt):
    pkt = pkt + seq_num
    return pkt


def add_updated_payload(payload, pkt):
    if sys.getsizeof(payload) > 8:
        payload = int.from_bytes(payload[0:8], byteorder='big')
    elif sys.getsizeof(payload) < 8:
        payload = int(payload.zfill(8))
    else:
        log_debug("byte value already 8")
    payload_length_bytes = payload.to_bytes(8, byteorder='big')
    pkt = pkt + payload_length_bytes
    return pkt


def send_packet_back(pkt):
    global net1
    out_interface = net1.interface_by_ipaddr(BLASTEE_IP)
    net1.send_packet(out_interface, pkt)


def print_packet(pkt):
    print(str(pkt))


def switchy_main(net):
    global net1, content_array
    net1 = net
    my_interfaces = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_interfaces]

    while True:
        gotpkt = True
        try:
            print("here1")
            timestamp, dev, pkt = net.recv_packet()
            log_debug("Device is {}".format(dev))
        except NoPackets:
            print("here2")
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            print("gotpacket")
            log_debug("I got a packet from {}".format(dev))
            log_debug("Pkt: {}".format(pkt))
            print_packet(pkt)
            print("here")
            content_array = pkt[RawPacketContents].data
            recd_seq_num = content_array[0:32]
            variable_payload_from_blastee = content_array[48:len(content_array)]

            pkt = set_ethernet_layer(pkt)
            pkt = set_ip_layer(pkt)
            pkt = set_transport_layer(pkt)

            pkt = add_seq_number(recd_seq_num, pkt)
            pkt = add_updated_payload(variable_payload_from_blastee, pkt)

            send_packet_back(pkt)
    net.shutdown()


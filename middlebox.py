#!/usr/bin/env python3

from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from threading import *
from random import *
import time

BLASTER_IP = "192.168.100.1"
BLASTER_MAC = "10:00:00:00:00:01"

MIDDLEBOX_BLASTER_IP = "192.168.100.2"
MIDDLEBOX_BLASTER_MAC = "40:00:00:00:00:01"

MIDDLEBOX_BLASTEE_IP = "192.168.200.2"
MIDDLEBOX_BLASTEE_MAC = "40:00:00:00:00:02"

BLASTEE_IP = "192.168.200.1"
BLASTEE_MAC = "20:00:00:00:00:01"


def set_ip_layer_middlebox_blastee(pkt):
    pkt[IPv4].src = MIDDLEBOX_BLASTEE_IP
    pkt[IPv4].dst = BLASTEE_IP
    return pkt


def set_ethernet_layer_middlebox_blastee(pkt):
    pkt[Ethernet].src = MIDDLEBOX_BLASTEE_MAC
    pkt[Ethernet].dst = BLASTEE_MAC
    return pkt


def set_transport_layer_middlebox_blastee(pkt):
    pkt[UDP].src = 4444
    pkt[UDP].dst = 5555
    return pkt


def set_ip_layer_middlebox_blaster(pkt):
    pkt[IPv4].src = MIDDLEBOX_BLASTER_IP
    pkt[IPv4].dst = BLASTER_IP
    return pkt


def set_ethernet_layer_middlebox_blaster(pkt):
    pkt[Ethernet].src = MIDDLEBOX_BLASTER_MAC
    pkt[Ethernet].dst = BLASTER_MAC
    return pkt


def set_transport_layer_middlebox_blaster(pkt):
    pkt[UDP].src = 4444
    pkt[UDP].dst = 5555
    return pkt


def read_parameters_from_file(param_file):
    with open(param_file) as data:
        substrings = data.read().split(" ")
        range_value = float(substrings[1])
        return range_value


def generate_random(range_value):
    drop_packet = False
    random_value = uniform(0, 1)
    if random_value < range_value:
        drop_packet = True
    return drop_packet


def switchy_main(net):
    my_intf = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_intf]
    myips = [intf.ipaddr for intf in my_intf]

    param_file = "middlebox_params.txt"

    while True:
        gotpkt = True
        try:
            timestamp, dev, pkt = net.recv_packet()
            log_debug("Device is {}".format(dev))
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            log_debug("I got a packet {}".format(pkt))

        if dev == "middlebox-eth0":
            log_debug("Received from blaster")
            '''
            Received data packet
            Should I drop it?
            If not, modify headers & send to blastee
            '''
            pkt = set_ethernet_layer_middlebox_blastee(pkt)
            pkt = set_ip_layer_middlebox_blastee(pkt)
            pkt = set_transport_layer_middlebox_blastee(pkt)

            range_value = read_parameters_from_file(param_file)
            drop_packet = generate_random(range_value)

            if drop_packet is True:
                log_debug("Dropping Packet")
            else:
                net.send_packet("middlebox-eth1", pkt)
        elif dev == "middlebox-eth1":
            log_debug("Received from blastee")
            '''
            Received ACK
            Modify headers & send to blaster. Not dropping ACK packets!

            '''
            pkt = set_ethernet_layer_middlebox_blaster(pkt)
            pkt = set_ip_layer_middlebox_blaster(pkt)
            pkt = set_transport_layer_middlebox_blaster(pkt)

            net.send_packet("middlebox-eth0", pkt)

        else:
            log_debug("Oops :))")

    net.shutdown()


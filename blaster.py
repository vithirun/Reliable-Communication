#!/usr/bin/env python3
from __future__ import division
from collections import OrderedDict
from switchyard.lib.address import *
from switchyard.lib.packet import *
from switchyard.lib.userlib import *
from random import randint
import time

BLASTER_IP = "192.168.100.1"
BLASTER_MAC = "10:00:00:00:00:01"

MIDDLEBOX_BLASTER_IP = "192.168.100.2"
MIDDLEBOX_BLASTER_MAC = "40:00:00:00:00:01"

MIDDLEBOX_BLASTEE_IP = "192.168.200.2"
MIDDLEBOX_BLASTEE_MAC = "40:00:00:00:00:02"

BLASTEE_IP = "192.168.200.1"
BLASTEE_MAC = "20:00:00:00:00:01"

ack_time = 0.0
sequence_number = lhs = rhs = 0
ack = OrderedDict()
ack_count = OrderedDict()
SWS = 0
Ip_address_blaster = 0
Number_of_packets = 0
length_of_variable_size_payload = 0
coarse_timeout = 0
recv_timeout = 0
total_start = total_end = 0
sequence_in_bytes = 0
Tot_bytes_without_duplicate = 0
Tot_bytes_with_duplicate = 0
original_count = 0
no_of_coarse_timeout = 0
net1 = None
ack_pkt_count = 0


def set_ip_layer(pkt):
    pkt[IPv4].src = BLASTER_IP
    pkt[IPv4].dst = MIDDLEBOX_BLASTER_IP
    return pkt


def set_ethernet_layer(pkt):
    pkt[Ethernet].src = BLASTER_MAC
    pkt[Ethernet].dst = MIDDLEBOX_BLASTER_MAC
    return pkt


def set_transport_layer(pkt):
    pkt[UDP].src = 4444
    pkt[UDP].dst = 5555
    return pkt


def set_seq_number(pkt):
    # pkt[3].sequence_number = sequence_number + 1
    # change it into bytes
    global sequence_number, sequence_in_bytes
    sequence_number += 1
    sequence_number_padding = int(str(sequence_number).zfill(32))
    sequence_in_bytes = sequence_number_padding.to_bytes(32, byteorder='big')
    pkt = pkt + sequence_in_bytes
    return pkt


def add_length(pkt):
    payload_length_bytes = int(str(length_of_variable_size_payload).zfill(16)).to_bytes(2, byteorder='big')
    pkt = pkt + payload_length_bytes
    return pkt


def add_payload(pkt):
    global Tot_bytes_without_duplicate, Tot_bytes_with_duplicate
    payload_value = 4444
    payload_value_bytes = payload_value.to_bytes(length_of_variable_size_payload, byteorder='big')
    pkt = pkt + payload_value_bytes
    return pkt


def add_pkt_to_window(pkt):
    ack[sequence_number] = [pkt, False]


def print_packet(pkt):
    print(str(pkt))


def send_packet(pkt):
    global original_count, net1
    original_count += 1
    out_interface = net1.interface_by_ipaddr(BLASTER_IP)
    net1.send_packet(out_interface, pkt)


def timeout():
    global ack_time
    diff = (time.time() - ack_time) * 1000
    if diff >= coarse_timeout:
        return True
    return False


def print_status(total_tx_time, resend_count, throughput, goodput):
    print("Total TX time" + str(total_tx_time))
    print("Number of reTX" + str(resend_count))
    print("Number of coarse TOs" + str(no_of_coarse_timeout))
    print("Throughput (Bps)" + str(throughput))
    print("Goodput (Bps)" + str(goodput))


def check_conditions(pkt):
    global SWS, lhs, rhs
    cond1 = cond2 = False
    if sequence_number == 1:
        lhs = rhs = 1

    # Condition 1
    last_ack_packet_idx = 0
    if rhs - lhs + 1 <= SWS:
        cond1 = True
        for key, value in ack.items():
            # print("value: ", value)
            if value[1] is True:
                last_ack_packet_idx = key
        # Condition 2
        if lhs > last_ack_packet_idx:
            cond2 = True
            rhs += 1
        else:
            log_debug("It has violated condition 2: Sj < Si")
    else:
        log_debug("It has violated condition 1: rhs - lhs + 1 <= SWS")
    return cond1, cond2


def switchy_main(net):
    global lhs, rhs, total_start, total_end, Tot_bytes_without_duplicate, Tot_bytes_with_duplicate, no_of_coarse_timeout
    global net1, ack_pkt_count
    resend_count = 0

    net1 = net
    my_intf = net.interfaces()
    mymacs = [intf.ethaddr for intf in my_intf]
    myips = [intf.ipaddr for intf in my_intf]

    param_file = "blaster_params.txt"

    read_parameters_from_file(param_file)

    while True:
        gotpkt = True
        try:
            # Timeout value will be parameterized!
            timestamp, dev, pkt = net.recv_packet(timeout=recv_timeout / 1000)
        except NoPackets:
            log_debug("No packets available in recv_packet")
            gotpkt = False
        except Shutdown:
            log_debug("Got shutdown signal")
            break

        if gotpkt:
            print("packet_recd is ........")
            print_packet(pkt)
            log_debug("I got a packet")
            # do recd_seq_num here
            content_array = pkt[RawPacketContents].data
            recd_seq_num = int.from_bytes(content_array[0:32], byteorder='big')
            # print("recd seq num: ", recd_seq_num)
            # recd_seq_num = int(recd_seq_num)
            if ack[recd_seq_num][1] is False:
                ack[recd_seq_num][1] = True
                ack_pkt_count += 1
                if ack_pkt_count >= Number_of_packets:
                    # Calculating everything here
                    total_end = time.time()
                    total_tx_time = total_end - total_start
                    # print("Total time:", total_tx_time)
                    Tot_bytes_without_duplicate = original_count * length_of_variable_size_payload
                    Tot_bytes_with_duplicate = resend_count * length_of_variable_size_payload
                    throughput = Tot_bytes_with_duplicate / total_tx_time
                    goodput = Tot_bytes_without_duplicate / total_tx_time

                    print_status(total_tx_time, resend_count, throughput, goodput)
                    break

                curr_packet_seq_num = recd_seq_num
                if curr_packet_seq_num > lhs:
                    print("packet ahs dropped and so Waiting for 300 ms (coarse timeout)........")
                    # time.sleep(coarse_timeout/1000)
                    if timeout() is True:
                        no_of_coarse_timeout += 1
                        for key, value in ack.items():
                            if value[1] is False:
                                # Resending the packets
                                resend_count += 1
                                send_packet(ack[key][0])
                else:
                    lhs += 1
            else:
                log_debug("Duplicate acknowledgement")
        #       TODO calculate time
        else:
            log_debug("Didn't receive anything")

            '''
            Creating the headers for the packet
            '''
            pkt = Ethernet() + IPv4() + UDP()
            pkt[1].protocol = IPProtocol.UDP

            '''
            Do other things here and send packet
            '''
            pkt = set_ethernet_layer(pkt)
            pkt = set_ip_layer(pkt)
            pkt = set_transport_layer(pkt)

            pkt = set_seq_number(pkt)
            pkt = add_length(pkt)
            pkt = add_payload(pkt)

            # add pkt to sender_window
            add_pkt_to_window(pkt)
            print("packet_sent is ........")
            print_packet(pkt)
            # Send the modified packet
            cond1, cond2 = check_conditions(pkt)
            if cond1 and cond2:
                if sequence_number == 1:
                    total_start = time.time()
                send_packet(pkt)
    net.shutdown()


def read_parameters_from_file(param_file):
    global Ip_address_blaster, Number_of_packets, length_of_variable_size_payload, SWS, coarse_timeout, recv_timeout
    with open(param_file) as data:
        substrings = data.read().split(" ")
        Ip_address_blaster = substrings[1]
        Number_of_packets = int(substrings[3])
        length_of_variable_size_payload = int(substrings[5])
        SWS = int(substrings[7])
        coarse_timeout = int(substrings[9])
        recv_timeout = int(substrings[11])


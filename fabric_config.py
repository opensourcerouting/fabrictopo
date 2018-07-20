#!/usr/bin/env python3

#
# fabric_config.py
#
# Copyright (c) 2018 by
# Network Device Education Foundation, Inc. ("NetDEF")
#
# Permission to use, copy, modify, and/or distribute this software
# for any purpose with or without fee is hereby granted, provided
# that the above copyright notice and this permission notice appear
# in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NETDEF DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NETDEF BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
#

"""
fabric_config.py: Generate Router and Topology configs based on JSON topo

"""

import os
import sys
import re
import argparse
import ipaddress
import json
#import ipaddr
from pprint import pprint


def router_number(routerName):
    """
    Returns the trailing number of the string
    Assuming the routers are named as some string followed by a sequential number, ie r1, r2 etc
    """
    return int(re.match('.*?([0-9]+)$', routerName).group(1))


def build_topo(json_topo):
    "Builds topology from json structure"

    # Now building the toplogy
    # Topology is built with direct P2P links, no switches between them

    # List of routers as read from structure.
    # Needed to mark which routers have the links already added
    listRouters = []

    # Create Topology - Step 1 STARTED routers:
    for routerN in sorted(json_topo['routers'].items(), key=len):
        if args.debug:
            print('Topo: Add router {}'.format(routerN[0]))
        # Add to list of routers
        listRouters.append(routerN[0])

    # Keep interfaces consistent - need to process list of routers
    # in predicatable order
    listRouters.sort(key=len)

    if 'link_ip_start' in json_topo:
        if 'ipv4' in json_topo['link_ip_start']:
            ipv4Next = ipaddress.IPv4Address(json_topo['link_ip_start']['ipv4'])
            ipv4Step = 2**(32-json_topo['link_ip_start']['v4mask'])
            if json_topo['link_ip_start']['v4mask'] < 31:
                ipv4Next += 1
        if 'ipv6' in json_topo['link_ip_start']:
            ipv6Next = ipaddress.IPv6Address(json_topo['link_ip_start']['ipv6'])
            ipv6Step = 2**(128-json_topo['link_ip_start']['v6mask'])
            if json_topo['link_ip_start']['v6mask'] < 127:
                ipv6Next += 1

    loopback_step_ipv4 = 2**(32-json_topo['lo_ip_start']['v4mask'])
    loopback_step_ipv6 = 2**(128-json_topo['lo_ip_start']['v6mask'])
    if args.debug:
        print('Loopback Step size: IPv4: {}, IPv6: {}'.format(loopback_step_ipv4, loopback_step_ipv6))

    # Create and save interface names as part of the link creation
    for router in listRouters:
        json_topo['routers'][router]['nextIfname'] = 0

    while listRouters != []:
        curRouter = listRouters.pop(0)
        for destRouter, data in sorted(json_topo['routers'][curRouter]['links'].items(), key=len):
            if destRouter in listRouters:
                # print("   Add connection from ", curRouter, " to ", destRouter)
                #
                # Set Interface names
                json_topo['routers'][curRouter]['links'][destRouter]['interface'] = \
                    'eth{}-{}-{}'.format(json_topo['routers'][curRouter]['nextIfname'], curRouter, destRouter)
                json_topo['routers'][destRouter]['links'][curRouter]['interface'] = \
                    'eth{}-{}-{}'.format(json_topo['routers'][destRouter]['nextIfname'], destRouter, curRouter)
                json_topo['routers'][curRouter]['nextIfname'] += 1
                json_topo['routers'][destRouter]['nextIfname'] += 1
                #
                # Set bandwidth
                if 'bandwidth' in json_topo['routers'][curRouter]['links'][destRouter]:
                    # Bandwidth specified - set same bandwidth on other side
                    json_topo['routers'][destRouter]['links'][curRouter]['bandwidth'] = \
                        json_topo['routers'][curRouter]['links'][destRouter]['bandwidth']
                else:
                    # Set default bandwidth
                    json_topo['routers'][curRouter]['links'][destRouter]['bandwidth'] = json_topo['default_bandwidth']
                    json_topo['routers'][destRouter]['links'][curRouter]['bandwidth'] = json_topo['default_bandwidth']
                #
                # Add IP addresses if auto-addressing requested
                if 'ipv4' in json_topo['routers'][curRouter]['links'][destRouter]:
                    # IPv4 address on this link
                    if json_topo['routers'][curRouter]['links'][destRouter]['ipv4'] == 'auto':
                        # Need to assign addresses for this link
                        json_topo['routers'][curRouter]['links'][destRouter]['ipv4'] = \
                            '{}/{}'.format(ipv4Next, json_topo['link_ip_start']['v4mask'])
                        #ipv4Next += 1
                        json_topo['routers'][destRouter]['links'][curRouter]['ipv4'] = \
                            '{}/{}'.format(ipv4Next+1, json_topo['link_ip_start']['v4mask'])
                        ipv4Next += ipv4Step
                if 'ipv6' in json_topo['routers'][curRouter]['links'][destRouter]:
                    # IPv6 address on this link
                    if json_topo['routers'][curRouter]['links'][destRouter]['ipv6'] == 'auto':
                        # Need to assign addresses for this link
                        json_topo['routers'][curRouter]['links'][destRouter]['ipv6'] = \
                            '{}/{}'.format(ipv6Next, json_topo['link_ip_start']['v6mask'])
                        #ipv6Next += 1
                        json_topo['routers'][destRouter]['links'][curRouter]['ipv6'] = \
                            '{}/{}'.format(ipv6Next+1, json_topo['link_ip_start']['v6mask'])
                        ipv6Next = ipaddress.IPv6Address(int(ipv6Next)+ipv6Step)
        #
        # Assign Loopback IPs
        if 'lo' in json_topo['routers'][curRouter]:
            if json_topo['routers'][curRouter]['lo']['ipv4'] == 'auto':
                json_topo['routers'][curRouter]['lo']['ipv4'] = \
                    '{}/{}'.format(ipaddress.IPv4Address(json_topo['lo_ip_start']['ipv4'])+(router_number(curRouter)*loopback_step_ipv4), \
                                   json_topo['lo_ip_start']['v4mask'])
            if json_topo['routers'][curRouter]['lo']['ipv6'] == 'auto':
                json_topo['routers'][curRouter]['lo']['ipv6'] = \
                    '{}/{}'.format(ipaddress.IPv6Address(json_topo['lo_ip_start']['ipv6'])+(router_number(curRouter)*loopback_step_ipv4), \
                                   json_topo['lo_ip_start']['v6mask'])
    return


def make_DataPlane_xml(json_topo, output):
    "Builds DataPlaneGraph.xml from json structure"

    output.write('<?xml version="1.0"?>\n')
    output.write('<DataPlaneGraph xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n')

    # List of routers as read from structure.
    # Needed to mark which routers have the links already added
    listRouters = []

    # Create Topology - Step 1 STARTED routers:
    for routerN in sorted(json_topo['routers'].items(), key=len):
        # Add to list of routers
        listRouters.append(routerN[0])

    # Keep interfaces consistent - need to process list of routers
    # in predicatable order
    listRouters.sort(key=len)

    while listRouters != []:
        curRouter = listRouters.pop(0)
        output.write('  <DeviceL3Info Hostname = "{}" >\n'.format(curRouter))
        for destRouter, data in sorted(json_topo['routers'][curRouter]['links'].items(), key=len):
            output.write('    <IPInterface AttachTo="{}" Prefix="None" />\n'.format(json_topo['routers'][curRouter]['links'][destRouter]['interface']))
        output.write('  </DeviceL3Info>\n')
    output.write('</DataPlaneGraph>\n')
    return


def make_PhysicalNet_xml(json_topo, output):
    "Builds PhysicalNetworkGraph.xml from json structure"

    output.write('<?xml version="1.0"?>\n')
    output.write('<PhysicalNetworkGraphDeclaration xmlns:xsd = "http://www.w3.org/2001/XMLSchema" xmlns:xsi = "http://www.w3.org/2001/XMLSchema-instance" >\n')

    # List of routers as read from structure.
    # Needed to mark which routers have the links already added
    listRouters = []

    # Create Topology - Step 1 STARTED routers:
    for routerN in sorted(json_topo['routers'].items(), key=len):
        # Add to list of routers
        listRouters.append(routerN[0])

    # Keep interfaces consistent - need to process list of routers
    # in predicatable order
    listRouters.sort(key=len)

    # Create Devices Section of XML
    output.write('  <Devices>\n')
    for curRouter in listRouters:
        output.write('    <Device xsi:type = "Router" Hostname = "{}" HwSku = "frr" />\n'.format(curRouter))        
    output.write('  </Devices>\n')

    # Create Device Interface Link Status
    output.write('  <DeviceInterfaceLinks>\n')
    while listRouters != []:
        curRouter = listRouters.pop(0)
        output.write('  <DeviceL3Info Hostname = "{}" >\n'.format(curRouter))
        for destRouter, data in sorted(json_topo['routers'][curRouter]['links'].items(), key=len):
            output.write('    <DeviceInterfaceLink xsi:type="DeviceInterfaceLink" ')
            output.write('StartDevice="{}" StartPort="{}" '.format(curRouter, json_topo['routers'][curRouter]['links'][destRouter]['interface']))
            output.write('EndDevice="{}" EndPort="{}" '.format(destRouter, json_topo['routers'][destRouter]['links'][curRouter]['interface']))
            output.write('Bandwidth="{}" />\n'.format(json_topo['routers'][destRouter]['links'][curRouter]['bandwidth']))
        output.write('  </DeviceL3Info>\n')
    output.write('  </DeviceInterfaceLinks>\n')

    # Finish XML
    output.write('</PhysicalNetworkGraphDeclaration>\n')

    return


def make_config(json_topo, routername, output):
    "Builds FRR Config from json structure for specified node"

    if routername not in json_topo['routers']:
        sys.stderr.write('Fatal: {} does not exist in topology!\n'.format(routername))
        quit()     

    conffile = open('/tmp/zebra.conf', 'w')
    output.write('frr defaults traditional\n!\n')
    output.write('hostname {}\n!\n'.format(routername))
    # Write Loopback Interface first
    output.write('interface lo\n')
    output.write(' description Loopback Router {}\n'.format(routername))
    output.write(' ip address {}\n'.format(json_topo['routers'][routername]['lo']['ipv4']))
    output.write(' ipv6 address {}\n'.format(json_topo['routers'][routername]['lo']['ipv6']))
    output.write(' ip router openfabric 1\n')
    output.write(' ipv6 router openfabric 1\n')
    output.write(' openfabric passive\n')
    output.write('!\n')
    # Write other interfaces
    for destRouter, data in sorted(json_topo['routers'][routername]['links'].items(), key=len):
        output.write('interface {}\n'.format(json_topo['routers'][routername]['links'][destRouter]['interface']))
        if 'ipv4' in json_topo['routers'][routername]['links'][destRouter]:
            # We have IPv4 address to configure
            output.write(' ip address {}\n'.format(json_topo['routers'][routername]['links'][destRouter]['ipv4']))
        if 'ipv6' in json_topo['routers'][routername]['links'][destRouter]:
            # We have IPv6 address to configure
            output.write(' ipv6 address {}\n'.format(json_topo['routers'][routername]['links'][destRouter]['ipv6']))
        output.write(' ip router openfabric 1\n')
        output.write(' ipv6 router openfabric 1\n')
        output.write('!\n')
    # Write OpenFabric config
    output.write('router openfabric 1\n')
    output.write(' net 49.0000.0000.{:04x}.00\n'.format(router_number(routername)))
    if 'openfabric' in json_topo['routers'][routername]:
        if 'tier' in json_topo['routers'][routername]['openfabric']:
            output.write(' fabric-tier {}\n'.format(json_topo['routers'][routername]['openfabric']['tier']))
    output.write('!\nend\n')

    return

###########################################################
# Main section
###########################################################

parser = argparse.ArgumentParser(description='Generate Topology and Router configs from JSON file')

parser.add_argument('jsontopo', type=argparse.FileType('r'), help='JSON file with topology configuration')
parser.add_argument('-p', '--dataplanexml', type=argparse.FileType('w'), help='Save DataPlaneGraph XML to specified file')
parser.add_argument('-n', '--physicalnetxml', type=argparse.FileType('w'), help='Save PhysicalNetworkGraph XML to specified file')
parser.add_argument('-r', '--router', type=str,  help='Router to generate the config for specified router')
parser.add_argument('-c', '--frrconfig', type=argparse.FileType('w'), help='Save Router config to specified file (Default: frr.conf)')
parser.add_argument('-d', '--debug', help='Turn on debug mode', action='store_true')

# parser.add_argument('echo')
args = parser.parse_args()

if args.debug:
    print(args)


###########################################################
# Done Parsing CLI, start reading the topology file
###########################################################

topo = json.loads(args.jsontopo.read())

build_topo(topo)

if args.dataplanexml != None:
    make_DataPlane_xml(topo, args.dataplanexml)

if args.physicalnetxml != None:
    make_PhysicalNet_xml(topo, args.physicalnetxml)

if args.router != None:
    if  args.frrconfig != None:
        conffile = args.frrconfig
    else:
        conffile = open('frr.conf', 'w')
    make_config(topo, args.router, conffile)

# Print calculated Topology
#pprint(topo, indent=2)



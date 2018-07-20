# OpenFabric Topology and FRR Config Generator

This small python script creates a XML DataPlaneGraph, PhysicalNetworkGraph
and FRR Router configurations for networks as defined in a JSON formatted 
topology

## Usage

```
usage: fabric_config.py [-h] [-p DATAPLANEXML] [-n PHYSICALNETXML] [-r ROUTER]
                        [-c FRRCONFIG] [-d]
                        jsontopo

Generate Topology and Router configs from JSON file

positional arguments:
  jsontopo              JSON file with topology configuration

optional arguments:
  -h, --help            show this help message and exit
  -p DATAPLANEXML, --dataplanexml DATAPLANEXML
                        Save DataPlaneGraph XML to specified file
  -n PHYSICALNETXML, --physicalnetxml PHYSICALNETXML
                        Save PhysicalNetworkGraph XML to specified file
  -r ROUTER, --router ROUTER
                        Router to generate the config for specified router
  -c FRRCONFIG, --frrconfig FRRCONFIG
                        Save Router config to specified file (Default:
                        frr.conf)
  -d, --debug           Turn on debug mode
```

### Examples

```
./fabric_config.py -p DataPlaneGraph.xml -n PhysicalNetworkGraph.xml small_clos_topo_numbered.json
```
`DataPlaneGraph.xml` and `PhysicalNetworkGraph.xml` are generated from 
topology defined in `small_clos_topo_numbered.json`

```
./fabric_config.py -r r13 small_clos_topo_numbered.json
```
`frr.conf` is created with FRR config for Router `r13` as defined in 
topology `small_clos_topo_numbered.json`

```
./fabric_config.py -r r13 -c /tmp/frr.conf small_clos_topo_numbered.json
```
`/tmp/frr.conf` is created with FRR config for Router `r13` as defined in 
topology `small_clos_topo_numbered.json`

## JSON definition

### Example with unnumbered interfaces (only IP on loopback)
```
{
"default_bandwidth": "10000",
"lo_ip_start": {"ipv4": "1.0.0.0", "v4mask": 32, "ipv6": "2001:DB8:F::", "v6mask": 128},
"routers": {
	"r0": {
        "started": 1,
		"lo": { "ipv4": "auto", "ipv6": "auto" },
        "links": {
        	"r4": {  },
        	"r5": { "bandwidth": "2000" },
        	"r6": {  },
        	"r7": {  }
        	},
        "openfabric": { "tier": 0 }
        },
    "r1": {
        "started": 1,
		"lo": { "ipv4": "auto", "ipv6": "auto" },
        "links": {
        	"r4": {  },
        	"r5": {  },
        	"r6": {  },
        	"r7": {  }
        	}
        },
    "r2": {
[...]
```

### Example with numbered interfaces (but have script assign IPs)

```
{
"default_bandwidth": "10000",
"link_ip_start": {"ipv4": "10.0.0.0", "v4mask": 31, "ipv6": "fd00::", "v6mask": 64}, 
"lo_ip_start": {"ipv4": "1.0.0.0", "v4mask": 32, "ipv6": "2001:DB8:F::", "v6mask": 128},
"routers": {
    "r0": {
        "started": 1,
        "lo": { "ipv4": "auto", "ipv6": "auto" },
        "links": {
            "r4": { "ipv4": "auto", "ipv6": "auto" },
            "r5": { "ipv4": "auto", "ipv6": "auto", "bandwidth": "2000" },
            "r6": { "ipv4": "auto", "ipv6": "auto" },
            "r7": { "ipv4": "auto", "ipv6": "auto" }
            },
        "openfabric": { "tier": 0 }
        },
    "r1": {
        "started": 1,
        "lo": { "ipv4": "auto", "ipv6": "auto" },
        "links": {
            "r4": { "ipv4": "auto", "ipv6": "auto" },
            "r5": { "ipv4": "auto", "ipv6": "auto" },
            "r6": { "ipv4": "auto", "ipv6": "auto" },
            "r7": { "ipv4": "auto", "ipv6": "auto" }
            }
        },
    "r2": {
[...]
```

### Description of the JSON fields

* `"default_bandwidth": "10000"`  
defines the default bandwitdh (only saved in Physical Network XML) 
for all links unless they have it specified on their own.

* `"link_ip_start": {"ipv4": "10.0.0.0", "v4mask": 31, "ipv6": "fd00::", "v6mask": 64}`  
(only required for topology with numbered interfaces)  
defines the start IP address range for numbering the interfaces and the 
network masks. Interfaces are numbered in sequence of the networks based
on the given masks

* `"lo_ip_start": {"ipv4": "1.0.0.0", "v4mask": 32, "ipv6": "2001:DB8:F::", "v6mask": 128}`  
defines the start IP address range for numbering the loopback interfaces 
and the network masks. Interfaces are numbered based on the trailing number
in their name as ipv4 + nodenumber + netblock_size_from_netmask,
eg node123 would be 1.0.0.0 + 123 * 1 

* `"routers": { }`  
Definition of all the routers in the topology. They start with the router name

* `"started": 1`  
Marks this node as started. Currently not used (starting of the nodes is 
outside of any frr config or xml configs)

* `"lo": { "ipv4": "auto", "ipv6": "auto" }`  
Loopback definition. In this example, IPv4 and IPv6 addresses are assigned and
are taken from the pool as defined by `lo_ip_start`.  
As an alternative, instead of `auto` a direct IP could be defined ie `172.16.1.1/32`

* `"links": { }`  
Definition of network interfaces to other openfabric routers. Destination 
are defined as example:

* `"r5": { "ipv4": "auto", "ipv6": "auto", "bandwidth": "2000" }`  
Connection to router `r5`, IPv4 and IPv6 addresses assigned from the pool
as defined in `link_ip_start` and override the default bandwidth to 2000

* `"openfabric": { "tier": 0 }`  
Defines the openfabric tier level for the node. Per OpenFabric Standard,
at least 2 routers need to be defined as openfabric tier 0


## Restrictions

* Routers are expected to be named in any way, but ending with a number, ie `R123` or `Node123`. The loopback
and the OpenFabric Net statement are generated in based on this last number (ie base IP + number)
* Currently only OpenFabric interfaces are configured and all interfaces are added to OpenFabric
* No Network Stub interfaces - all interfaces (except loopback) are connected to another OpenFabric Router

#!/usr/bin/env python3
import sys
import xmltodict
from time import sleep
from pyftdi.i2c import *

def mk_getmap(register):
    values = {}
    for d in register["Data"]:
        values[int(d["#text"], 16)] = d["@Desc"]
    return values

def mk_setmap(register):
    values = {}
    for d in register["Data"]:
        values[d["@Desc"]] = int(d["#text"], 16)
    return values

def read_register(port, register):
    length = 1
    if "Length" in register:
        length = int(register["Length"])

    bin = port.read_from(int(register["Command"], 16), length)
    value = int.from_bytes(bin, 'little')

    type = "Hex"
    if "@Type" in register:
        type = register["@Type"]

    if type == "Hex":
        return "{0:0{1}X}".format(value, length*2)
    elif type == "List":
        return mk_getmap(register)[value]
    elif type == "Math":
        return round(value*float(register["Math"]["Factor"]), 2)

def write_register(port, register, value):
    length = 1
    if "Length" in register:
        length = int(register["Length"])

    type = "Hex"
    if "@Type" in register:
        type = register["@Type"]

    if type == "Hex":
        value = int(value, 16)
    elif type == "List":
        value = mk_setmap(register)[value]
    elif type == "Math":
        value = round(value/float(register["Math"]["Factor"]))
    else:
        return

    bin = value.to_bytes(length, 'little')
    port.write_to(int(register["Command"], 16), bin)

def detect_device(port, device):
    if "Detect" in device and device["Detect"]["@Type"] == "RegisterMatch":
        register = device["Detect"]["Register"]
        data = register["Data"]
        return read_register(port, register) == data
    return False

def print_section(port, section, device):
    items = device[section]["Item"]
    for item in items:
        value = read_register(port, item["Register"])
        print("{}: {}".format(item["Name"], value))

if(len(sys.argv) != 2):
    print("Usage {} somefile.xml".format(sys.argv[0]))
    sys.exit(1)

file = open(sys.argv[1], "r")
contents = file.read()
dict = xmltodict.parse(contents)
file.close()

if "EVC2" not in dict:
    print("Not an EVC2 XML file?")
    exit(1)

device = dict["EVC2"]["Device"]
name = device["Name"]

i2c = I2cController()
i2c.configure('ftdi://ftdi:232h/1', frequency=10000)
port = i2c.get_port(0x11)

# FFFFFFUUUUUU
try:
    port.read(0)
except I2cNackError:
    sleep(0.1)
    i2c = I2cController()
    i2c.configure('ftdi://ftdi:232h/1', frequency=10000)
    port = i2c.get_port(0x11)

print("Looking for {}...".format(name))
if detect_device(port, device):
    print("{} detected!".format(name))
else:
    print("Failed :(")
    exit(1)

print("\nDevice:")
print_section(port, "Constant", device)
print("\nConfiguration:")
print_section(port, "Configuration", device)
print("\nMonitoring:")
print_section(port, "Monitoring", device)

# TODO: make a better interface for this, or a GUI
# write_register(port, device["Configuration"]["Item"][4]["Register"], 30)
# write_register(port, device["Configuration"]["Item"][5]["Register"], 50)
# write_register(port, device["Configuration"]["Item"][6]["Register"], 25)
# write_register(port, device["Configuration"]["Item"][1]["Register"], "Disabled")
# write_register(port, device["Configuration"]["Item"][10]["Register"], "Yes")

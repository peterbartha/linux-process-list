#!/usr/bin/env python3
'''

Create XML tree from Linux client processes.

Created on 2015.04.05.
@author: Peter Bartha

'''

# Import useful scripts
import sys
import csv
import os.path
import argparse
from xml.dom.minidom import Document
try:
    import lmiwbem
except ImportError as ie:
    print("(ERROR) Cannot import lmiwbem package. If is not installed please install it with: '$ sudo yum install lmiwbem'")
    sys.exit(1)

# Initialization for Argument Parser and parsing source file, output path and (optionally) identity arguments
parser = argparse.ArgumentParser()
parser.add_argument("-s", "--source", help="source file name with path", type=str, action="store", required=True)
parser.add_argument("-o", "--output", help="output file path", type=str, action="store", required=True)
parser.add_argument("-i", "--identity", help="task id", type=int)
args = parser.parse_args()

# Check source file existing
if not os.path.exists(args.source):
    print("(ERROR) Source file (" + args.source + ") does not exists.")
    sys.exit(2)

# Check output file existing
if not os.path.exists(args.output):
    print("(ERROR) Output file path (" + args.output + ") not exists.")
    sys.exit(3)

# Identity number greater than 0
if args.identity is not None and args.identity < 0:
    print("(ERROR) Quantity shall be a positive number (and greater than 0).")
    sys.exit(4)

# Reading source CSV file line-by-line
with open(args.source) as source:
    reader = csv.reader(source, delimiter=',')  # Open a CSV reader

    firstFound = args.identity is None  # Checking the given process identity argument to exists and added to document
    lineNum = 0
    for line in reader:
        lineNum += 1
        if lineNum == 1:
            # Missing header column in source file
            if len(line) < 3:
                print("(ERROR) Missing connection parameter columns in " + args.source + " input file!")
                sys.exit(5)

            # Check header column name validity
            if line[0].upper() != "HOST" or line[1].upper() != "USER" or line[2].upper() != "PASSWORD":
                print("(ERROR) Bad source header found! Correct " + args.source +
                      " CSV file header: Host,User,Password")
                sys.exit(6)
        else:
            # check existence of the connection parameters
            if len(line) < 3:
                print("(WARNING) Missing connection parameters at line " + str(lineNum) + " in " + args.source +
                      " input file!")
                continue

            # Setting up variables for lmiwbem connection
            host = line[0]
            username = line[1]
            password = line[2]

            # Skip this line if hostname not provided
            if host == "":
                print("(WARNING) Missing hostname at line " + str(lineNum) + " in " + args.source + " input file!")
                continue

            # Skip this line if username not provided
            if username == "":
                print("(WARNING) Missing username at line " + str(lineNum) + " in " + args.source + " input file!")
                continue

            filename = args.output + '/' + host + '.xml'
            httpHost = 'http://' + host
            cls = 'CIM_Process'

            try:
                # Connect to CIMOM
                conn = lmiwbem.WBEMConnection()
                conn.connect(httpHost, username, password)

                # Enumerate Instances (selecting useful properties)
                processes = conn.EnumerateInstances(cls, 'root/cimv2', LocalOnly=False, DeepInheritance=True,
                                                    IncludeQualifiers=True, IncludeClassOrigin=True,
                                                    PropertyList=['Name', 'Handle', 'ParentProcessID'])

                # Open and create XML document to write
                output = open(filename, 'w')
                doc = Document()

                # Create root element
                root = doc.createElement('Processes')
                doc.appendChild(root)

                # Iterating over processes
                for process in processes:
                    # Getting process values
                    id = int(process.items()[0][1])
                    name = process.items()[1][1]
                    parentId = int(process.items()[2][1])

                    # Create an entry element with its attributes
                    elem = doc.createElement('Process')
                    elem.setAttribute("ID", str(id))
                    # elem.setAttribute("Parent", str(parentId))  # visual test only
                    elem.setAttribute("Name", name)

                    # Check
                    if not firstFound:
                        if id == args.identity:
                            # Add element which id is equal with args.identity (only once)
                            root.appendChild(elem)
                            firstFound = True
                    else:
                        if args.identity is None and parentId == 0:
                            root.appendChild(elem)  # direct child of root element

                        # Finding parent of actual element by parentId
                        elementList = doc.getElementsByTagName('Process')
                        for parent in elementList:
                            if parent.getAttribute('ID') == str(parentId):
                                parent.appendChild(elem)
                                break

                # Close connection with CIMOM
                conn.disconnect()

                # Write document, and after unlink it and close output XML file
                doc.writexml(output, addindent="    ", newl='\n')
                doc.unlink()
                output.close()

            except lmiwbem.lmiwbem_core.ConnectionError as connErr:
                print("(ERROR) You cannot connect to " + host)
                print("\t" + str(connErr))
                continue

# Closing source CSV file
source.close()

import subprocess
import re
from datetime import datetime
import csv
from pathlib import Path
import mysql.connector
import jasontools


def parseEnvFile(itemName):
    itemSecret = os.getenv(str(itemName))

    if itemSecret:
        try:
            jsonFormat = json.loads(itemSecret)
            return jsonFormat

        except:
            return itemSecret
    else:
        return itemSecret

db_config = jasontools.parseEnvFile("DB_CONFIG")

def addAddress(ip,mac,name):

    address = findAddress(mac)

    if address != []:
        print(address)
        return None

    query = """
        INSERT INTO ipcontrol (ip,mac,name)
        VALUES (%s,%s,%s)
    """

    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()

    cursor.execute(query, (
        ip,mac,name
    ))
    
    print(f"New IP added {name} |{ip} | {mac}")

    db.commit()

def logNetwork():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # log_message = f"{current_time} {owner} | {state}"
    #Get the time

    #Check if they have changed state

    #If changed sate update log 
    
    
    
    return None

def findAddress(mac):
    query = """
        SELECT *
        FROM ipcontrol
        WHERE mac = (%s)
    """

    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()

    cursor.execute(query, (mac,))

    response = cursor.fetchall()

    addressdata = []

    for row in response:
        rowData = {
            "id" : row[0],
            "ip" : row[1],
            "mac" : row[2],
            "name" : row[3],
            "whitelisted" : row[4],
            "owner" : row[5]
        }

        addressdata.append(rowData)

    cursor.close()
    db.close()

    if len(addressdata) == 1:
        return addressdata[0]
    else:
        return addressdata

def scan_network():
    try:
        result = subprocess.run(['sudo', 'arp-scan', '--localnet'], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Failed to run arp-scan")
            return
        
        output = result.stdout
        
        #print(output)
        
        pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:]+)\s+(.+)')
        
        matches = pattern.findall(output)
    
        #print(matches)
        scanMatches = {}

        for match in matches:
            ip, mac, mac_owner = match
            
            scanMatches[mac] = {
                "IP" : ip,
                "MAC" : mac,
                "MAC_Owner" : mac_owner
                }
            #collateConnectedIPStoCSV(ip, mac, mac_owner)
        
        print(scanMatches)
        print("Scanning Home Networking...")

        for add in scanMatches:
            print(add)
            add_ip = scanMatches[add]['IP']
            add_mac = scanMatches[add]['MAC']
            add_owner = scanMatches[add]['MAC_Owner']

            addAddress(add_ip,add_mac,add_owner)

        return scanMatches
    
    except Exception as e:
        print(f"An error occurred: {e}")
        return e

if __name__ == "__main__":
    scan_network()

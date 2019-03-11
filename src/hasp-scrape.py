import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import matplotlib.animation as animation
import matplotlib.backends.tkagg as tkagg
import tkinter as tk
import numpy as np
import urllib
import os
import time
import sys
import logging
import threading
from requests import get
from requests.exceptions import RequestException
from contextlib import closing
from bs4 import BeautifulSoup
from datetime import datetime
from struct import *
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
#from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT
from matplotlib.figure import Figure
from tkinter import *


# Declare constants
DIRECTORY = os.getcwd()
PLOT_PATH = DIRECTORY + "/2018_analysis/plots.pdf"
url = "https://laspace.lsu.edu/hasp/groups/2018/data/data.php?pname=Payload_12&py=2018"
FLIGHT_BEGIN = "09/02/18 8:00:00"
FLIGHT_BEGIN_DT = datetime.strptime(FLIGHT_BEGIN, "%m/%d/%y %I:%M:%S")
WAIT_TIME = 60 # Number of seconds between new packet checks
PACKET_STRUCTURE = ['mp_temp (C)', 'rpi_temp (C)', 'counts', 'dose (uGy/min)', 'frame', 'zero', 'time']
PLOT_SQUARE_SIZE = int(np.ceil(np.sqrt(len(PACKET_STRUCTURE) - 3)))

ACCEPTED_COMMANDS = ['0x01', '0x02', '0x03'] # These are currently dummy commands

# Plotting objects
fig = plt.gcf()
# fig.patch.set_facecolor('xkcd:grey') # Changes color of the GUI background
plt.style.use("fast")
fig.set_size_inches(12, 10)
#fig.show()
plt.rcParams.update({'font.size': 24})
cmap = plt.cm.get_cmap("gist_rainbow", len(PACKET_STRUCTURE))
hasp_data = []
plot_list = []
threadList = []


# Drop-down menu tool functions
def toolsMenuDoNothing():
    print('Okay.')

def toolsMenuSendCommand():
    command = simpledialog.askstring('Input', 'Enter the command:', parent=window)
    if command in ACCEPTED_COMMANDS:
        answer = messagebox.askyesno('Confirm','Confirm command: ' + command) # Open new box to confirm choice
        if answer: # answer is a bool
            # Upload the command to the HASP spreadsheet. For now it will send to a dummy sheet.
            os.system('python ' + DIRECTORY + '/src/send-command.py ' + command) # Had to do this bc Google Sheets API does not work with Python3
            logging.info('Sent command: \'' + command + '\'')
            statusText.set('Sent command: \'' + command + '\'')
    else:
        logging.info('Command not recognized: \'' + command + '\'')
        statusText.set('Command not recognized: \'' + command + '\'')
        messagebox.showwarning("Warning", "Command not recognized.")
        
def toolsMenuSavePlots():
    fig.savefig(PLOT_PATH, bbox_inches='tight')
    logging.info("Figure saved to \"" + PLOT_PATH.split("/")[-1] + "\"")

# This currently does not work properly.
def toolsMenuExit():
    end_log_e(None, None)

# tkinter objects
width, height = 200, 100
window = tk.Tk()
tcanvas = FigureCanvasTkAgg(fig, window)

# Create the tkinter drop-down menu
menu = Menu(window)
window.config(menu=menu)
toolsMenu = Menu(menu)
menu.add_cascade(label='Tools', menu=toolsMenu)
toolsMenu.add_command(label='Send Command', command=toolsMenuSendCommand)
toolsMenu.add_separator()
toolsMenu.add_command(label='Save Plots', command=toolsMenuSavePlots)
toolsMenu.add_separator()
toolsMenu.add_command(label='Exit', command=toolsMenuExit)

#Create status bar at bottom of GUI so that the terminal does not need to be monitered.
statusText = StringVar(window)
statusText.set("Initializing HASP-RTP")
statusbar = Label(window, textvariable=statusText, bd=1, relief=SUNKEN, anchor=W).pack(side=BOTTOM, fill=X)

# Prevents plots being made for packet num and timestamp
for i in range(1, len(PACKET_STRUCTURE) + 1):
    if i == 5 or i == 6 or i == 7:
        continue
    
    temp_plot = fig.add_subplot(PLOT_SQUARE_SIZE, PLOT_SQUARE_SIZE, i)
    plot_list.append(temp_plot)
    data, = temp_plot.plot([], [], "r")
    hasp_data.append(data)

def simple_get(url):

    try:
        with closing(get(url, stream = True)) as resp:
            if is_good_response(resp):
                return resp.content

            else:
                return None

    except RequestException as e:
        logging.error("Error during requests to {0} : {1}".format(url, str(e)))
        return None


def is_good_response(resp):
    
    content_type= resp.headers["Content-Type"].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find("html") > -1)


def compare_times(t1, t2):
    
    difference = t2 - t1

    return difference.days
    

def find_table(html):
    
    logging.info("Searching for table...")
    table = html.find("table")
    logging.info("... table found.")

    return table


# Gathers table data that only corresponds to flight
def read_table(table):
    
    rows = []
    columns = []
    packets = []
    packet_urls = []

    # Check if rows exist
    logging.info("Searching for rows...")
    rows = table.find_all("tr")[1:] #Take all rows except the header
    if len(rows) is not 0:
        logging.info(" ... rows found.")

    else:
        end_log_e("No rows found. Exitting...\n", None)
        
    # Check if columns exist
    logging.info("Searching for columns...")
    if rows[0].get_text() is not "":
        logging.info("... columns found.")

    else:
        end_log_e("No columns found. Exitting...\n", None)        

    # Creates a list of packet names and a list of packet urls
    logging.info("Extracting packet metadata...")
    for row in rows:
        packet_string = ""
        columns = row.find_all("td")

        for column in columns:
            packet_string += column.get_text()

            # Prevents a "," from being added at the end of the packet string
            if "KB" not in packet_string:
                packet_string += ","

        # Filter out non-flight packets
        string_list = packet_string.split(",")
        string_time = string_list[1].strip(" AM").strip(" PM")
        string_dt = datetime.strptime(string_time, "%m/%d/%y %H:%M:%S")
        if compare_times(FLIGHT_BEGIN_DT, string_dt) >= 0: # Excludes packets that were uploaded prior to the beginning of flight
            packets.append(packet_string.split(",")[0] + "," + str(float(packet_string.split(",")[2].split(" ")[0])) + " KB") # Adds packet data string to list
            packet_url = url.split("data.php")[0] + columns[0].find_all("a")[0].get("href") # Finds link to download packet
            packet_urls.append(packet_url) # Adds download link to list
            
    logging.info("... completed.\n")
    
    return packets, packet_urls


def get_new_packets(packet_list, packet_urls, dir_files, last_dir_file):

    if dir_files == None:
        return packet_list, packet_urls

    if (set(packet_list).issubset(dir_files)) or packet_list == []: # Checks if new packets need to be downloaded
        logging.info("Local repository is up-to-date. Retrying in " + str(WAIT_TIME) + " seconds...\n")
        statusText.set("Local repository is up-to-date. Retrying in " + str(WAIT_TIME) + " seconds...")
        for _ in range(1000):
            window.update()
            time.sleep(WAIT_TIME/1000) # Wait before checking for a new/updated packet 
        #end_log_e(None, None) # I didn't want to create a new function to end the program, so I cheated by using end_log_e()

        # Sleeping in the main thread messes with the qt event loop
        # This loop allows plots to remain responsive while waiting for new packets

        # I commented this out because I'm now using tkinter to display the plots, so plt.pause() shouldn't
        # be needed anymore. In addition, there was an incompatibility
        #for _ in range(1000):
        #    plt.pause(WAIT_TIME/1000)

        return None, None

    else:
        logging.info("Downloading updated/missing files...")
        
        new_packet_list = []
        new_url_list = []
        for i, packet in enumerate(packet_list):
            if packet not in dir_files:
                new_packet_list.append(packet_list[i])
                new_url_list.append(packet_urls[i])
            
        return new_packet_list, new_url_list


def download(link, fileLocation, fileSize):
    logging.info("Downloading " + fileLocation.split('/')[-1] + " [" + fileSize + "]...")
    res = urllib.request.urlopen(link)
    raw = open(DIRECTORY + "/2018_raw_files/" + fileLocation.split('/')[-1], "wb")
    raw.write(res.read())
    raw.close()
    logging.info(fileLocation.split('/')[-1] + " [" + fileSize + "] completed.")
    
def newDownloadThread(link, fileLocation, fileSize):
    download_thread = threading.Thread(target=download, args=(link,fileLocation,fileSize))
    threadList.append(download_thread)
    download_thread.start()
    
def download_data(packet_list, packet_urls):
    try:
        logging.info("Downloading packets...\n")
        # Create a thread for downloading each  existing files on the HASP website
        for i, packet in enumerate(packet_list):    
            packet = packet.split(",")
            packet_name = packet[0]
            packet_size = packet[1] 
            newDownloadThread(packet_urls[i], DIRECTORY + '/2018_raw_files/' + packet_name, packet_size)

        #Plot all the files
        for i, packet in enumerate(packet_list):
            while threadList[i].isAlive(): # Prevents an undownloaded file from being plotted
                time.sleep(0.1)
            plot_data(packet.split(',')[0])
            
        # Save plot once completed
        fig.savefig(PLOT_PATH, bbox_inches='tight')
        logging.info("Figure saved to \"" + PLOT_PATH.split("/")[-1] + "\"\n")
    except Exception as e:
        end_log_e(e, packet_name)

        
def plot_data(packet_name):
    new_data = []
    for i in range(0, len(hasp_data) + 1):
        new_data.append([])
    message = "Updating plot with data from " + packet_name
    logging.info(message)
    statusText.set(message)
    data_file = open(DIRECTORY + "/2018_raw_files/" + packet_name, "r", errors = "ignore")
    for line in data_file:
        data_string = data_file.readline().strip("\n")        
        broken_data_string = data_string.split(",")
        if len(broken_data_string) != 7:
            continue
        broken_data_string.pop(-1)
        broken_data_string.pop(-1)
        for i, measurement in enumerate(broken_data_string):
            # Handles possibly corrupted data where a value is not a number, resulting in a conversion error
            try:
                measurement = float(measurement)
            except Exception as e:
                logging.warning("String \"" + measurement + "\" found instead of numerical value in position \"" + PACKET_STRUCTURE[i] + "\" of data frame number " +str(broken_data_string[-1]) + ". Replacing with 0.")
                measurement = 0

            # Prevents an updated data packet from being plotted twice
            if broken_data_string not in hasp_data[0].get_xdata():
                new_data[i].append(measurement)
            else:
                continue
            
            # Plots update every 50 packets
            if len(new_data[-1]) % 50 == 0 and len(new_data[-1]) != 0:

                #hasp_data[-1].set_xdata(np.append(hasp_data[-1].get_xdata(), new_data[-1]))

                #print(len(hasp_data[-1].get_xdata()))
                
                for i, sensor in enumerate(PACKET_STRUCTURE):
                    if sensor == "frame" or sensor == "zero" or sensor == "time":
                        continue
                    
                    #print(new_data[i])
                    sensor_plot = plot_list[i]
                    hasp_data[i].set_xdata(np.append(hasp_data[i].get_xdata(), new_data[-1]))
                    hasp_data[i].set_ydata(np.append(hasp_data[i].get_ydata(), new_data[i]))
                    color = cmap(i)
                    hasp_data[i].set_color(color)
                    sensor_plot.set_xlabel("Packet Number")
                    sensor_plot.set_ylabel(PACKET_STRUCTURE[i])
                    sensor_plot.set_xlim(0, max(hasp_data[0].get_xdata()))
                    sensor_plot.set_ylim(min(hasp_data[i].get_ydata()) * 0.9, max(hasp_data[i].get_ydata()) * 1.1)
                    window.update()
                
                fig.tight_layout()                
                fig.canvas.flush_events()
                fig.canvas.draw()
                
                tcanvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH)#.grid(row=0, column=2, sticky='E')
                tcanvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)#.grid(row=0, column=2, sticky='E')#

                window.update_idletasks()
                window.update()
                
                # Empty new_data after every plot update
                new_data = []
                
                for i in range(0, len(hasp_data) + 1):
                    new_data.append([])
                    

def create_dirs():
    dir_files = os.listdir(DIRECTORY)
    if "2018_raw_files" not in dir_files:
        os.makedirs(DIRECTORY + "/2018_raw_files")

    if "2018_analysis" not in dir_files:
        os.makedirs(DIRECTORY + "/2018_analysis")

# Finds the last packet in the local repository.
def get_directory_info():
    
    # Get files in directory
    dir_files = os.listdir(DIRECTORY + "/2018_raw_files")
    
    # Checks if the directory is empty.
    if len(dir_files) == 0:
        return None, None

    # Sorts files from A - Z
    dir_files.sort()

    # Adds a tag to each file's name specifying the file size 
    for i, dfile in enumerate(dir_files):
        dir_files[i] = dfile + "," + str(float(float(os.path.getsize(DIRECTORY + "/2018_raw_files/" + dir_files[i])) / 1000)) + " KB"

    # Takes the last file in the directory (AKA the most recent data packets)
    last_dir_file = dir_files[-1]

    return dir_files, last_dir_file


# Controls the sequencing of the processes acquiring and handling the data
def get_data():
    
    response = simple_get(url)
    html = BeautifulSoup(response, "html.parser")
    
    if response is not None:

        # Find most recently downloaded data packet
        directory_files, last_packet = get_directory_info()
        
        # Check if a table exists
        packet_table = find_table(html)

        # Read the table's rows and columns to gather metadata from each data packet
        data_packets, urls = read_table(packet_table)

        # Get list of new .raw files and their urls
        data_packets, urls = get_new_packets(data_packets, urls, directory_files, last_packet)

        # Download the new .raw files
        if data_packets != None and urls != None:
            download_data(data_packets, urls)
        #fig.tight_layout()
        #fig.canvas.flush_events()
        #fig.canvas.draw()
        

# Ends the log with exception e
def end_log_e(e, packet_name):
    logging.info("------------------------------------------------------------")
    if packet_name is not None:
        logging.error("Error handling packet: " + packet_name)
        
    if e is not None:
        logging.error(e)

    fig.savefig(PLOT_PATH, bbox_inches='tight')
    logging.info("Figure saved to \"" + PLOT_PATH.split("/")[-1] + "\"")
        
    logging.info("------------------------------------------------------------")
    logging.info("------------------------------------------------------------")
    logging.info("END LOG")
    logging.info("------------------------------------------------------------")
    logging.info("------------------------------------------------------------")
    sys.exit(0)

    
if __name__  == "__main__":
    try:
        create_dirs()

        # Delete any preexisting raw files
        dir_files = os.listdir(DIRECTORY + "/2018_raw_files")
        for f in dir_files:
            os.remove(DIRECTORY + "/2018_raw_files/" + f)
        
        # Setup logger
        logging.basicConfig(level = logging.DEBUG,
                            format = "%(asctime)s %(name)+12s: %(levelname)-8s %(message)s",
                            filename = DIRECTORY + "/2018_analysis/scrape.log",
                            filemode = "w")

        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(name)s: %(levelname)-8s %(message)s')
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)
        logging.getLogger("matplotlib").setLevel(logging.WARNING) # Suppresses matplotlib debug
        
        logging.info("------------------------------------------------------------")
        logging.info("------------------------------------------------------------")
        logging.info("BEGIN LOG")
        logging.info("URL: " + url)
        logging.info("File path: " + DIRECTORY)
        logging.info("------------------------------------------------------------")
        logging.info("------------------------------------------------------------\n")

        while True:
            get_data()
            
        logging.info("------------------------------------------------------------")
        logging.info("------------------------------------------------------------")
        logging.info("END LOG")
        logging.info("------------------------------------------------------------")
        logging.info("------------------------------------------------------------")
        
    except KeyboardInterrupt:
        fig.savefig(PLOT_PATH, bbox_inches='tight')
        logging.info("Figure saved to \"" + PLOT_PATH + "\"")

        logging.info("Keyboard Interrupt. Exitting...\n")
        logging.info("------------------------------------------------------------")
        logging.info("------------------------------------------------------------")
        logging.info("END LOG")
        logging.info("------------------------------------------------------------")
        logging.info("------------------------------------------------------------")

    except Exception as e:
        end_log_e(e, None)

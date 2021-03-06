# HASP-RTP #
Real-time plotter (RTP) built to display HASP data as it becomes available and to send commands to the payload.

#### \*_WIP_ \* #### 
---

This simple script is designed to aid in monitoring data collection during the testing/integration and flight stages of the HASP mission. Unless either of the two previously mentioned events is taking place, this script will plot the 2017 flight data from the SORA payload.

### How To ###
- Run the program by typing `$./run.sh` in the terminal, then hit enter. 
--* Note that a second attempt at running the program will cause an error. To relieve this, use the `./flush.sh` command to remove all analysis and raw data files

### Current Features ###
- Prior to downloading the packets, the script scans the directory for packets that have already been downloaded. If a downloaded file was updated on the HASP website since the last time the script checked the website, the script will download the updated file (resulting in no loss of data). It will only download and plot the packets which have not been downloaded yet. 
- The script will scrape all relevent data packets from the HASP website. As it downloads each packet, it updates plots for each physical measurement. The script will discard any data not belonging to the SORA payload as well as corrupted data.
- The script does not slow down as more data is downloaded and processed, despite the large quantity of data.
- The plots are embedded within a Tkinter GUI.
- Commands can be sent directly from the GUI to the command center. Credentials are needed for this feature. These credentials are not included for security reasons.

# CTA-2045 UCM with Raspberry Pi Libraries

Software package to use a Raspberry Pi as a CTA-2045 UCM for a grid-connected water heater.

### Key features
- Installation script to quickly install all dependencies and compile the code
- Basic scheduling tool 

_Please note this is a pre-alpha proof of concept demonstration, and it has only been tested once. There may be bugs or glitches._

## Requirements
1. Raspberry Pi: We tested with 3B+ and other models _should_ work
    1. MicroSD card, at least 32 GB
    2. Computer monitor & display cables to the Pi (it may also be possible to SSH to the Pi)
    3. Mouse & keyboard
    4. Power supply
2. [USB to RS-485 adapter](https://www.amazon.com/dp/B081MB6PN2)
3. AWG 22 wire. Note: for short lengths (<10cm) between the adapter and the port on the water heater, it should work fine with regular wire. Longer lengths are recommended to use shielded wire to prevent signal interference. If purchasing shielded wire, only 2 strands are necessary. 
5. CTA-2045 compatible water heater (may work with other SGD)

## Installation

1. Use [Raspberry PI Imager](https://www.raspberrypi.com/software/operating-systems/) from another computer to install Raspbian/Raspberry Pi OS with Desktop, 32-bit (Tested with the version from 13 May 2025, Kernel 6.12, Debian 12). Other versions probably will work too.
    - When setting it up, the username must be “pi”. If you use another username, something in the C++ code will fail later on. You can fix that by creating a new user called “pi”, but then adjusting all the sudoer and auto login permissions is a pain so best to just start with a user called “pi”. The name of the Raspberry Pi device can be anything. 

3. Connect the Raspberry Pi to a power supply, display, mouse, and keyboard. Insert the SD card. 
4. Download or clone this repo. For best results, make sure it is under `/home/pi/water_heaters_testings`
5. Run the installation script and follow the prompts there. 
```bash
cd water_heaters_testings
sudo bash CTA2045_UCM_Installer.sh
```
6. Restart the Raspberry Pi
7. Assemble the system as shown in the figure below. 
    - Pin 1: B- (blue wire in the photo)
    - Pin 7: A+ (green wire in the photo)

![Photo of wiring for Raspberry Pi, RS-485, and CTA-2045](https://github.com/bwooshem/water_heaters_testings/blob/main/docs/pi-to-water-heater-via-s485-connections.png)

## Usage

### Mode Options

| Mode | Letter | Code | Notes | 
| -- | -- | -- | -- | 
| CriticalPeakEvent | c | 5 | -- | 
| EndShed | e | 6 | Returns system to default mode |
| Shed | s | 7 | -- |
| GridEmergency | g | 8 | Shuts all heating elements |
| Loadup | l | 9 | -- |
| OutsideCommunication  | o | 10 | Send this first to initialize receiving signals (performed automatically in the launcher script) |

### Setting a schedule
Create (or edit) the file called `demo_schedule.csv`. The file should have 2 columns, "Time Elapsed" in seconds, and "Mode". The launcher will run the mode listed after the specified time since the start of the run has elapsed. For example, in the table below, it will run "l" for load up at 30s, "s" for shed at 120s, and "c" for critical peak at 360s. Note that it will keep sending the last mode in the file indefinitely. For a mode left running for more than 5 minutes, the code re-sends the mode every 5 minutes to ensure the water heater keeps the mode setting. 

| Time Elapsed \[s\] | Mode |
| -- | -- |
| 30 | l |
| 120 | s |
| 360 | c |
| ... | ... |

### Running the launcher script
```bash
cd water_heaters_testings
sudo python3 launcher.py
```

The launcher script will follow the schedule specified in demo_schedule.csv

#### Known Issues & Future Additions
- Sometimes the signals are not properly received by the device. If so, the code will report `app nak received`. The launcher will reattempt up to 3 times, after which it will crash. So far, the only reliable solution is to restart the Pi and the SGD.
- Signals are only sent when certain outputs are received from the UCM C++ code, typically every 1 minute. When multiple signals are within 60s of each other, sometimes the first signal doesn't get sent. Signals are delayed until the outputs are received, so it may occur up to 60s after when it was initially intended to run.
- Currently only supports a few CTA-2045A signals.
- Future work includes adding AdvancedLoadUp and the ability to query the water heater for current status. 

## Acknowledgements

This package is based on the [water_heaters_testings project by Portland State Power Lab](https://github.com/PortlandStatePowerLab/water_heaters_testings)

The [CTA-2045 UCM C++ Library](https://github.com/epri-dev/CTA-2045-UCM-CPP-Library.git) was originally developed by EPRI
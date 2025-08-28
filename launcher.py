import subprocess
import time
import os
from datetime import datetime, timedelta
import signal
import csv

# --- Configuration ---
# The command to use for elevated privileges.
SUDO_COMMAND = 'sudo'
# The path to your compiled 'sample2' executable.
EXECUTABLE_PATH = 'dcs/build/debug/sample2'
# Path to schedule file, with 2 columns and 1 header row. [ time [s] | mode ]
SCHEDULE_PATH = 'demo_schedule.csv'
# start_time =  datetime.now() 
attempts = 0
prior_mode = 'n'
most_recent_time = datetime.now() 
resend_interval = 5 * 60
NUM_RETRIES = 3

# def get_choice_to_send():
#     """
#     This function determines what character to send to the sample2 program.
#     For now, it's a placeholder that always returns 's'.
#     """
#     time.sleep(1)
#     now = datetime.now()
#     dt = abs((now-start_time).total_seconds())
#     if dt % 120 <40:
#         mode = 'l'
#     elif dt % 120 <80:
#         mode = 's'
#     else: 
#         mode = 'c'

#     print(f"[Launcher] Determined mode: '{mode}'")
#     return mode

def get_schedule(file_path):
    time_list = []
    mode_list = []
    
    with open(file_path, mode='r', newline='') as csvfile:
        csvreader = csv.reader(csvfile)
        headers = next(csvreader)  # Skip the header row
        
        for row in csvreader:
            time_list.append(float(row[0]))  # Convert time to float
            if float(row[0]) < 1: print("Warning: Start time can't be less than 1s. ")
            mode_list.append(row[1])          # Mode is a string
            
    return time_list, mode_list

def run_and_interact():
    global now
    global most_recent_time
    global prior_mode, attempts

    print("[Launcher] Beginning UCM Launcher Code. To exit program, use Ctrl + c ")

    times, modes = get_schedule(SCHEDULE_PATH)
    # ack = [False] * len(times)

    """
    Launches the sample2 program with sudo and handles the interaction loop.
    """
    if not (os.path.exists(EXECUTABLE_PATH) and os.access(EXECUTABLE_PATH, os.X_OK)):
        print(f"Error: The program '{EXECUTABLE_PATH}' was not found or is not executable.")
        print("Please make sure you have compiled sample2.c and it's in the correct path.")
        return

    # The command is now a list including 'sudo'
    command_to_run = [SUDO_COMMAND, EXECUTABLE_PATH]
    
    print(f"[Launcher] Starting '{' '.join(command_to_run)}' as a subprocess...")

    # Launch the process.
    # NEW: We add 'sudo' to the command list.
    # NEW: We redirect stderr to stdout to catch any error messages from the C program.
    process = subprocess.Popen(
        command_to_run,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, # Merge stderr into stdout
        text=True,
        bufsize=1 
    )

    print("[Launcher] UCM process started...")

    try:
        # Initialization. Must start by sending a "o" to begin handling outside communication
        i = 0
        sent = False
        while i < 77: #catchsafe; expect about at most 30 lines of stuff
            if process.poll() is not None:
                print("[Launcher] Subprocess has terminated unexpectedly.")
                break

            output_line = process.stdout.readline()

            if not output_line:
                print("[Launcher] End of output stream. Subprocess has finished.")
                break

            print(f"[UCM Output] {output_line.strip()}")

            # put ack received first, because sometimes after received, it prints out the options menu followed by enter choice again
            if ("app ack received" in output_line): # if acknowledged, this loop is done. Move on to the actual communication (main loop)
                print("[Launcher] Successfully initialized :)")
                attempts = 0
                break
            elif ("enter choice:" in output_line) and (not sent): # If ready to accept input
                command_to_send = str("o\n")
                print(f"[Launcher] Sending o- OutsideCommunication to initialize...")
                process.stdin.write(command_to_send) # don't encode() otherwise get TypeError: write() argument must be str, not bytes
                process.stdin.flush()
                sent = True
            elif ("app nak received" in output_line): # Not acknowledged. Need to try again
                sent = False
                attempts += 1
                time.sleep(3) #wait 3s then try again
            
            if attempts > NUM_RETRIES: #if it fails too many consecutive times
                print("[Launcher] Error: device did not initialize communication in 3 attempts. Cleanly exiting & disconnecting the program.")
                kill_command = [SUDO_COMMAND, 'kill', str(process.pid)]
                print(f"[Launcher] Running: {' '.join(kill_command)}")
                subprocess.run(kill_command)
                raise CommunicationFailedError(
                    "[Launcher] Device did not initialize communication in 3 attempts. Terminating  :("
                )
            i += 1

        # count actual start time as when it's properly initialized
        start_time =  datetime.now() 
        most_recent_time = datetime.now() 
        t = 0
        attempts = 0
        print("[Launcher] Beginning sending signals using following schedule: ")
        print(times)
        print(modes)
        sent = False

        # main loop
        while True:
            if process.poll() is not None:
                print("[Launcher] Subprocess has terminated unexpectedly.")
                break

            output_line = process.stdout.readline()

            if not output_line:
                print("[Launcher] End of output stream. Subprocess has finished.")
                break

            print(f"[UCM Output] {output_line.strip()}")

            now = datetime.now()
            dt_start = abs((now-start_time).total_seconds())
            dt_prev = abs((now-most_recent_time).total_seconds())

            if (dt_prev > resend_interval): # if it's time to automatically resend the command, reset the attempts so it can start sending 
                attempts = 0
                sent = False
            if ((t+1)<len(times)) and (float(times[t+1]) < float(dt_start)): # increment to next line in schedule if next line exists and we're at that time
                t += 1
                sent = False
                attempts = 0
                print("[Launcher] Preparing to send schedule item", t, "   mode:", modes[t])

            if ("app ack received" in output_line): # if acknowledged, don't send again
                attempts= 0
                # t += 1 #don't increment here, because of auto resend
            elif ("app nak received" in output_line):
                sent = False
                time.sleep(2) #wait 2s
            elif (("enter choice:" in output_line) | ("operational state received" in output_line)) and not sent: # If ready to accept input
                
                print("[Launcher] Current times since start: ", dt_start, "   since previous: ", dt_prev)

                if  (attempts < NUM_RETRIES):

                    # mode = modes[t]
                    command_to_send = str(f"{modes[t]}\n")

                    print(f"[Launcher] Sending '{modes[t]}' to subprocess...")
                    process.stdin.write(command_to_send)
                    process.stdin.flush()
                    sent = True
                    attempts += 1
                    most_recent_time = datetime.now()
                    time.sleep(1) #wait for response
                else:
                    print(f"[Launcher] Not resending '{modes[t]}' because it has failed to acknowledge too many times: {attempts}")


                

    except KeyboardInterrupt:
        print("\n[Launcher] Keyboard interrupt received. Shutting down...")
    finally:
        if process.poll() is None:
            print("[Launcher] Terminating the subprocess.")
            # We need to use sudo to kill the process as well, since it's running as root.
            # A simple process.terminate() might fail due to permissions.
            # A more robust way is to kill it directly using its process ID (pid).
            kill_command = [SUDO_COMMAND, 'kill', str(process.pid)]
            print(f"[Launcher] Running: {' '.join(kill_command)}")
            subprocess.run(kill_command)
        
        print("[Launcher] Cleanup complete. Exiting.")


if __name__ == "__main__":
    run_and_interact()
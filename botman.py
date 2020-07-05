import argparse
import subprocess
import os
import time

parser = argparse.ArgumentParser(description="Start the bots")
parser.add_argument('botnames', type=str, nargs='+', help='Usernames(s) of bot(s) to start')
args = parser.parse_args()

# check if all the requested bots exist
for botname in args.botnames:
	mainfile = f"main_{botname}.py"
	if not os.path.exists(mainfile):
		raise Exception("ERROR: can't find {mainfile}")

# start the bots
processes = []
for botname in args.botnames:
	mainfile = f"main_{botname}.py"
	bot_process = subprocess.Popen(['python3', mainfile])
	processes.append(bot_process)

print("Processes started.")
for process in processes:
	print(process)


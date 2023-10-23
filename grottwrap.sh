#!/bin/bash

# turn on bash's job control
#set -m

#python3 -u grott.py -v &

# Start the helper process
python3 -u grottserver.py -v &

python3 -u grott.py -v

# the my_helper_process might need to know how to wait on the
# primary process to start before it does its work and returns


# Wait for any process to exit
wait

# Exit with status of process that exited first
exit $?

# now we bring the primary process back into the foreground
# and leave it there
#fg %1

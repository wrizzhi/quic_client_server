# to run the ptp.c program 
1. compille the program gcc ptp.c -o ptp
2. Slave must be started first.
3. to run as master- ./ptp -m "slave IP"
4. to run as slave - ./ptp -s "master IP"


#TO RUN CHANGETIME
1. Compile using gcc
2. Run timedatectl set-ntp false
3. RUN PROGRAM
4. Run timedatectl set-ntp false when done

#TO RUN SHAPER.SH

1. LATENCY=10ms sudo -E ./shaper.sh start eth0 100Mbit
2. sudo -E ./shaper.sh clear eth0 

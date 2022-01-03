from queue import Queue
from QUIC_Server import quicconnectserver
import ParserServer
import time
import sys
import threading


def processing(server,data_queue):
    
    time_start = time.time()
    
    while True:
        if data_queue and  time.time() - time_start < 10:
            
            frame = data_queue.get()
            t2 = time.time()
        
            if ( frame["time_taken"] + (t2 - frame["t1"]) < 0.15):
                print("frame ",frame["id"]," processing")
                time.sleep(0.03)
                server_reply = frame["id"] + "processed"
                server.quic_obj.server_send(server_reply)
                time_start = time.time()
            else:
                print("frame ",frame["id"]," dropped")
                server_reply = frame["id"] + "dropped"
                server.quic_obj.server_send(server_reply)

def main():
    print("entered server code")

    
    args = ParserServer.parse("Parse server args")
    data_queue = Queue()
    j = quicconnectserver(args.host,args.port,args.certificate, args.private_key,args.verbose)
    prc_thread = threading.Thread(target=processing,args=(j,data_queue))
    prc_thread.start()
    counter = 0
    while True:
        id,f,t=j.quic_obj.recieve()
        if id:
            temp = dict()
            temp["frame"] = f
            temp["time_taken"] = t
            temp["t1"] = time.time()
            temp["id"] = id
            print("frame",id,"time",t)
            data_queue.put(temp)
            
        else:
            if counter > 10:
                exit()
            counter+=1
            
            

if __name__ == "__main__":
    main()

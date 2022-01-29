import random
import zmq
from multiprocessing import Process, Barrier
import os
import time

#  kill $(sudo lsof -t -i:5550)

def broadcast_failure(msg, proposer, N, prob):
    for i in range(N):
        send_failure(msg, proposer, i, prob)
    pass

def broadcast_to_other_nodes(msg, proposer, N):
    for i in range(N):
        if(i != proposer):
            send(msg, proposer, i) # Send without failure possibility
    pass

def send(msg, proposer, target):
    json_msg = {"sender_id": proposer, "receiver_id": target, "msg": msg}
    push_sockets[target].send_json(json_msg)
    #time.sleep(0.3)

def send_failure(msg, proposer, target, prob):
    if(random.random() <= prob):
        json_msg = {"sender_id": proposer, "receiver_id": target, "msg": "CRASH {}".format(proposer)}
    else:
        json_msg = {"sender_id": proposer, "receiver_id": target, "msg": msg}
    push_sockets[target].send_json(json_msg)
    #time.sleep(0.3)
    pass

def paxos_node(barrier, id, prob, N, val, num_rounds):
    
    pid = os.getpid()
    #print("PAXOS PROCESS STARTS: {} {}".format(pid, id))

    global pull_socket
    global push_sockets

    push_sockets = []

    # Creates a PULL socket
    context = zmq.Context()

    pull_socket = context.socket(zmq.PULL)
    base = 5550
    port = base + id
    pull_socket.bind(f"tcp://127.0.0.1:{port}")

    # Creates PUSH sockets
    for i in range(N):
        push_socket = context.socket(zmq.PUSH)
        base = 5550
        port = base + i
        push_socket.connect(f"tcp://127.0.0.1:{port}")
        push_sockets.append(push_socket)

    # Maximum round number this node has voted for
    max_voted_round = -1
    max_voted_val = None

    # Value proposed by this node in the latest round in which it is the proposer and it has collected join messages from a majority of nodes.
    propose_val = None
    decision = None
    node_role = None

    sent_propose = False
    for r in range(num_rounds):
        # Leader of the round r
        leader_id = r % N
        node_role = "PROPOSER" if id == leader_id else "ACCEPTOR"

        if(node_role == "PROPOSER"):

            print("ROUND {} STARTED WITH INITIAL VALUE {}".format(id, val))
            broadcast_failure("START", leader_id, N, prob)
            # If the proposer does not receive a START message, it receives a CRASH for its place which will interpreted as failure of this node as an acceptor as well ????
            join_msgs = []
            num_received_msgs = 0
            num_start_msgs = 0
            num_join_msgs = 0
            start_taken_from_itself = False

            # PHASE 1 STARTS
            while(num_received_msgs != N):
                try:
                    pull_socket.RCVTIMEO = 200
                    recv_json_msg = pull_socket.recv_json()
                    num_received_msgs += 1

                    #print("LEADER OF {} RECEIVED IN JOIN PHASE: {}".format(r, recv_json_msg['msg']))
                    print("PROPOSER {}, ROUND {}, JOIN PHASE: {}".format(id,r,recv_json_msg))

                    if("START" in recv_json_msg['msg']):
                        #num_start_msgs += 1
                        # Receiving its own START message is interpreted as a successful join to this round
                        if(recv_json_msg['sender_id'] == id and recv_json_msg['target_id'] == id):
                            start_taken_from_itself = True
                            num_join_msgs += 1
                        else:
                            num_start_msgs += 1
                            
                    elif("JOIN" in recv_json_msg['msg']):
                        num_join_msgs += 1
                        join_msg = {'sender_id': recv_json_msg['sender_id'], 'max_voted_round': int(recv_json_msg['msg'].split()[1]), 'max_voted_val': recv_json_msg['msg'].split()[2]}
                        join_msgs.append(join_msg)

                except:
                    
#print("num_received_msgs",num_received_msgs)
                    pass
            
            if(num_join_msgs + num_start_msgs > N / 2):
                
                # Take the message with maximum voted round field
                join_msgs = sorted(join_msgs, key=lambda d: d['max_voted_round'], reverse=True)

                max_voted_round_of_msg = join_msgs[0]['max_voted_round']
                max_voted_val_of_msg = join_msgs[0]['max_voted_val']

                propose_val = None if max_voted_val_of_msg == 'None' else int(max_voted_val_of_msg)
                #print("propose_val", join_msgs[0])
                
                # Should we use local max_voted_round or join msg max voted round variable??
                '''
                if(start_taken_from_itself and max_voted_round_of_msg == -1):
                    print("propose_val")
                    propose_val = val
                '''

                if(max_voted_round_of_msg == -1):
                    propose_val = val
                
                #print("propose_val", propose_val, join_msgs[0], val)
                broadcast_failure("PROPOSE {}".format(propose_val), leader_id, N, prob)
                sent_propose = True
                
            elif(num_join_msgs + num_start_msgs <= N / 2):
                broadcast_to_other_nodes("ROUNDCHANGE", leader_id, N)
                print("LEADER OF ROUND {} CHANGED ROUND".format(r))
                barrier.wait()
                continue

            # Maybe there should be a barrier in here? because if may not be 
            if(sent_propose):
                num_received_msgs = 0
                num_vote_msgs = 0
                num_propose_msgs = 0
                recv_msgs_alos = []
                while(num_received_msgs != N):
                    try:
                        pull_socket.RCVTIMEO = 200
                        recv_json_msg = pull_socket.recv_json()
                        num_received_msgs += 1
                        recv_msgs_alos.append(recv_json_msg)

                        #print("LEADER OF {} RECEIVED IN VOTE PHASE: {}".format(r, recv_json_msg['msg']))
                        
                        print("PROPOSER {}, ROUND {}, VOTE PHASE: {}".format(id,r,recv_json_msg))

                        if("VOTE" in recv_json_msg['msg']):
                            num_vote_msgs += 1

                        elif("PROPOSE" in recv_json_msg['msg']):
                            if(recv_json_msg['sender_id'] == id and recv_json_msg['receiver_id'] == id):
                                # Should i increase vote too?
                                num_vote_msgs += 1
                                max_voted_round = r
                                max_voted_val = propose_val
                            else:
                                num_propose_msgs += 1
                    except:
                        pass
                
                print("id {}, round {}, num_received_msgs {}, num_vote_msgs {}, num_propose_msgs {}, \n messages: {}".format(id, r, num_received_msgs, num_vote_msgs, num_propose_msgs, recv_msgs_alos))
                if(num_vote_msgs + num_propose_msgs > N/2):
                    decision = propose_val
                    barrier.wait()

                print("LEADER OF {} DECIDED ON VALUE: {}".format(r, decision))
                
                continue
            
        elif(node_role == "ACCEPTOR"):
            recv_msgs = []
            num_received_msgs = 0

            # Need a timeout??
            #pull_socket.RCVTIMEO = 100

            # Receive Message P1?
            # There is a problem, acceptors go to other round just by passing this timeout value!
            try:
                pull_socket.RCVTIMEO = 200
                recv_json_msg = pull_socket.recv_json()
                
                #print("ACCEPTOR {} RECEIVED IN JOIN PHASE: {}".format(id, recv_json_msg['msg']))
                print("ACCEPTOR {}, ROUND {}, JOIN PHASE: {}".format(id, r, recv_json_msg))

                # Responding to round proposer or sender_id ? taken from message?? but crash r % N ?? maybe not sender?
                if("START" in recv_json_msg['msg']):
                    send_failure("JOIN {} {}".format(max_voted_round, max_voted_val), leader_id, leader_id, prob)

                elif("CRASH" in recv_json_msg['msg']):
                    send("CRASH {}".format(r % N), leader_id, leader_id)
            except:
                pass
        
            try:
                pull_socket.RCVTIMEO = 200
                # Recieve message P2?
                recv_json_msg = pull_socket.recv_json()
                
                #print("ACCEPTOR {} RECEIVED IN VOTE PHASE: {}".format(id, recv_json_msg['msg']))
                print("ACCEPTOR {}, ROUND {}, VOTE PHASE: {}".format(id, r, recv_json_msg))

                # Send to proposer of round r?? or 
                if("PROPOSE" in recv_json_msg['msg']):
                    max_voted_round = r
                    max_voted_val_of_msg = recv_json_msg['msg'].split()[1]
                    max_voted_val = None if max_voted_val_of_msg == 'None' else int(max_voted_val_of_msg)
                    send_failure("VOTE", leader_id, leader_id, prob)
                    barrier.wait()
                    continue

                elif("CRASH" in recv_json_msg['msg']):
                    send("CRASH {}".format(r % N), leader_id, leader_id)
                    continue
                
                elif("ROUNDCHANGE" in recv_json_msg['msg']):
                    barrier.wait()
                    continue
            except:
                pass

if __name__ == '__main__':

    os.system('kill $(sudo lsof -i:5550)')
    os.system('kill $(sudo lsof -i:5551)')
    os.system('kill $(sudo lsof -i:5552)')
    os.system('kill $(sudo lsof -i:5553)')

    num_proc = 4
    prob = 0.1
    num_rounds = 3
    N = num_proc
    val = 0 # 0 or 1 binary value
    sockets = None
    barrier = Barrier(N, timeout=50)
    paxos_nodes = [Process(target=paxos_node, args=(barrier, id, prob, N, val, num_rounds)) for id in range(num_proc)]
        
    for pn in paxos_nodes:
        pn.start()
        pass

    for pn in paxos_nodes:
        pn.join()
        pass
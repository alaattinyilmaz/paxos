# paxos
Synchronous Paxos algorithm implementation.

# requirements

    pip install zmq
    
# run
  numNodes: number of nodes, crashProb: crash probability, numRounds: number of rounds 
  
    python paxos.py numNodes, crashProb, numRounds 


# synchronous-paxos-algorithm

The main feature of the synchronous Paxos is that nodes run together in a synchronous or lock-step way.  At any time, all nodes are more or less at the same phase of the same round. The biggest difference between two nodes is one phase i.e., one node can be in Phase 2 of round r whereas another node can be in Phase 1 of round r + 1 but no node can be in Phase 2 of round r + 1 or Phase 1 of round r in this case. Since the system is synchronous, we assume that channels are reliable and bounded i.e., there are no message losses and we can put a finite and fixed upper bound on the message delays. Although having a synchronous system is impossible in general (over internet and WAN), nodes (processes) of your Paxos will run on the same machine. Therefore, we can safely assume fast and reliable
communication among nodes. However, our implementation tolerate node failures. We assume that nodes can have crash-recovery failures i.e., they can be unavailable for a limited amount of time, but they cannot forge arbitrary messages or send messages on behalf of others. Paxos algorithm works correctly if at most k out of 2k + 1 nodes fail at any time even if the failing sets are different at different points in time. We will relax this requirement and allow a node to fail at any point in time according to a probability. This probability will be one of the inputs to your program and it will be known to all nodes.

In our implementation, we did not really crash Paxos nodes (processes) by terminating or suspending them, but we simulated a crash by sending CRASH messages from failing nodes. Before sending a message, each node will randomly decide whether to send the correct message expected by the algorithm or a CRASH message simulating a node failure. Probability of sending a CRASH message will be determined according to the input probability mentioned before. The CRASH
messages are independent in the sense that probability of node failures does not depend on previously send or received messages. Please note that round leaders
(proposers) might fail and send CRASH messages as well. 

In order to implement failure semantics described above, we wrapped the
original message send method with another method sendFailure (msg, proposer, target, prob) that sends "CRASH proposer" message to the target with probability prob and sends msg to the target with probability 1−prob. We also implemented failure-aware broadcast method broadcastFailure (msg, proposer, N, prob) that calls sendFailure(msg, proposer, i, prob) for all i ∈ [0, N − 1].

Here, proposer is the node ID of the leader of the current round that the sender node is in. The sender or the receiver do not have to be the proposer. You can
use proposer field to differentiate CRASH messages from different rounds. As you can imagine, probabilistic failure might cause more than half of nodes
to fail at any time. Similar to the asynchronous setting, this only affects the termination property and agreement and validity properties must still hold. We
will ensure termination by letting nodes run for a fixed and predefined number of rounds. They will run for these amount whether they reach to multiple decisions
or none.

# detailed-specifications

Please click [here](https://github.com/alaattinyilmaz/paxos/blob/main/paxos-specs.pdf) link to read all spesifications.

# further-read

[The Part-Time Parliament by Leslie Lamport](https://lamport.azurewebsites.net/pubs/lamport-paxos.pdf)

[Paxos Made Simple by Leslie Lamport](https://lamport.azurewebsites.net/pubs/paxos-simple.pdf)

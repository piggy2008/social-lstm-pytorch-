'''
ST-graph data structure script for the structural RNN implementation
Takes a batch of sequences and generates corresponding ST-graphs

Author : Anirudh Vemula
Date : 15th March 2017
'''
import numpy as np
from helper import getVector, getMagnitudeAndDirection


class ST_GRAPH():

    def __init__(self, batch_size=50, seq_length=5, dataset_dim=[760, 1280]):
        '''
        Initializer function for the ST graph class
        params:
        batch_size : Size of the mini-batch
        seq_length : Sequence length to be considered
        '''
        self.batch_size = batch_size
        self.seq_length = seq_length
        self.dataset_dim = dataset_dim
        self.nodes = [{} for i in range(batch_size)]
        self.edges = [{} for i in range(batch_size)]

    def reset(self):
        self.nodes = [{} for i in range(self.batch_size)]
        self.edges = [{} for i in range(self.batch_size)]

    def readGraph(self, source_batch):
        '''
        Main function that constructs the ST graph from the batch data
        params:
        source_batch : List of lists of numpy arrays. Each numpy array corresponds to a frame in the sequence.
        '''
        for sequence in range(self.batch_size):
            # source_seq is a list of numpy arrays
            # where each numpy array corresponds to a single frame
            source_seq = source_batch[sequence]
            for framenum in range(self.seq_length):
                # Each frame is a numpy array
                # each row in the array is of the form
                # first row:  [car_id, centreX, centreY, height, width, d_min, d_max, feature_img_name]
                # other rows: [car_id, centreX, centreY, height, width, d_min, d_max]
                frame = source_seq[framenum]

                # Add nodes
                for ped in range(frame.shape[0]):
                    pedID = frame[ped][0]
                    x = (int(frame[ped][1]) - self.dataset_dim[0]/2.) / self.dataset_dim[0]
                    y = (int(frame[ped][2]) - self.dataset_dim[1]/2.) / self.dataset_dim[1]
                    pos = (x, y)

                    if pedID not in self.nodes[sequence]:
                        node_type = 'H'
                        node_id = pedID
                        node_pos_list = {}
                        node_pos_list[framenum] = pos
                        self.nodes[sequence][pedID] = ST_NODE(node_type, node_id, node_pos_list)
                    elif framenum - 1 in self.nodes[sequence][pedID].node_pos_list:
                        self.nodes[sequence][pedID].addPosition(pos, framenum)

                        # Add Temporal edge between the node at current time-step
                        # and the node at previous time-step
                        edge_id = (pedID, pedID)
                        pos_edge = (self.nodes[sequence][pedID].getPosition(framenum-1), pos)
                        if edge_id not in self.edges[sequence]:
                            edge_type = 'H-H/T'
                            edge_pos_list = {}
                            # ASSUMPTION: Adding temporal edge at the later time-step
                            edge_pos_list[framenum] = pos_edge
                            self.edges[sequence][edge_id] = ST_EDGE(edge_type, edge_id, edge_pos_list)
                        else:
                            self.edges[sequence][edge_id].addPosition(pos_edge, framenum)
                    else:
                        # this means this ID appeared in the previous frame but disapear and reappear in the current frame
                        continue

                # ASSUMPTION:
                # Adding spatial edges between all pairs of pedestrians.
                # TODO:
                # Can be pruned by considering pedestrians who are close to each other
                # Add spatial edges
                for ped_in in range(frame.shape[0]):
                    for ped_out in range(ped_in+1, frame.shape[0]):
                        pedID_in = frame[ped_in][0]
                        pedID_out = frame[ped_out][0]
                        pos_in = ((int(frame[ped_in][1])-self.dataset_dim[0]/2.)/self.dataset_dim[0]/2.,
                                  (int(frame[ped_in][2])-self.dataset_dim[1]/2.)/self.dataset_dim[1]/2.)

                        pos_out = ((int(frame[ped_out][1])-self.dataset_dim[0]/2.)/self.dataset_dim[0]/2.,
                                   (int(frame[ped_out][2])-self.dataset_dim[1]/2.)/self.dataset_dim[1]/2.)
                        pos = (pos_in, pos_out)
                        edge_id = (pedID_in, pedID_out)
                        # ASSUMPTION:
                        # Assuming that pedIDs always are in increasing order in the input batch data
                        if edge_id not in self.edges[sequence]:
                            edge_type = 'H-H/S'
                            edge_pos_list = {}
                            edge_pos_list[framenum] = pos
                            self.edges[sequence][edge_id] = ST_EDGE(edge_type, edge_id, edge_pos_list)
                        else:
                            self.edges[sequence][edge_id].addPosition(pos, framenum)

    def printGraph(self):
        '''
        Print function for the graph
        For debugging purposes
        '''
        for sequence in range(self.batch_size):
            nodes = self.nodes[sequence]
            edges = self.edges[sequence]

            print('Printing Nodes')
            print('===============================')
            for node in nodes.values():
                node.printNode()
                print('--------------')

            print
            print('Printing Edges')
            print('===============================')
            for edge in edges.values():
                edge.printEdge()
                print('--------------')

    def getSequence(self, ind):
        '''
        Gets the data related to the ind-th sequence
        '''
        nodes = self.nodes[ind]
        edges = self.edges[ind]

        numNodes = len(nodes.keys())
        list_of_nodes = {}

        retNodes = np.zeros((self.seq_length, numNodes, 2))
        retEdges = np.zeros((self.seq_length, numNodes*numNodes, 3))  # Diagonal contains temporal edges
        retNodePresent = [[] for c in range(self.seq_length)]
        retEdgePresent = [[] for c in range(self.seq_length)]
        retNodePresentName = [[] for c in range(self.seq_length)]

        for i, ped in enumerate(nodes.keys()):
            list_of_nodes[ped] = i
            pos_list = nodes[ped].node_pos_list
            for framenum in range(self.seq_length):
                if framenum in pos_list:
                    retNodePresent[framenum].append(i)
                    retNodePresentName[framenum].append(ped)
                    retNodes[framenum, i, :] = list(pos_list[framenum])

        for ped, ped_other in edges.keys():
            i, j = list_of_nodes[ped], list_of_nodes[ped_other]
            edge = edges[(ped, ped_other)]

            if ped == ped_other:
                # Temporal edge
                for framenum in range(self.seq_length):
                    if framenum in edge.edge_pos_list:
                        retEdgePresent[framenum].append((i, j))
                        # retEdges[framenum, i*(numNodes) + j, :] = getVector(edge.edge_pos_list[framenum])
                        retEdges[framenum, i*numNodes + j, :] = getMagnitudeAndDirection(edge.edge_pos_list[framenum])
            else:
                # Spatial edge
                for framenum in range(self.seq_length):
                    if framenum in edge.edge_pos_list:
                        retEdgePresent[framenum].append((i, j))
                        retEdgePresent[framenum].append((j, i))
                        # the position returned is a tuple of tuples

                        retEdges[framenum, i*(numNodes) + j, :] = getMagnitudeAndDirection(edge.edge_pos_list[framenum])
                        retEdges[framenum, j*numNodes + i, 0] = np.copy(retEdges[framenum, i*(numNodes) + j, 0])
                        retEdges[framenum, j*numNodes + i, 1:3] = -np.copy(retEdges[framenum, i*(numNodes) + j, 1:3])

        return retNodes, retEdges, retNodePresent, retEdgePresent, retNodePresentName

    def getBatch(self):
        return [self.getSequence(ind) for ind in range(self.batch_size)]


class ST_NODE():

    def __init__(self, node_type, node_id, node_pos_list):
        '''
        Initializer function for the ST node class
        params:
        node_type : Type of the node (Human or Obstacle)
        node_id : Pedestrian ID or the obstacle ID
        node_pos_list : Positions of the entity associated with the node in the sequence
        '''
        self.node_type = node_type
        self.node_id = node_id
        self.node_pos_list = node_pos_list

    def getPosition(self, index):
        '''
        Get the position of the node at time-step index in the sequence
        params:
        index : time-step
        '''
        assert(index in self.node_pos_list)
        return self.node_pos_list[index]

    def getType(self):
        '''
        Get node type
        '''
        return self.node_type

    def getID(self):
        '''
        Get node ID
        '''
        return self.node_id

    def addPosition(self, pos, index):
        '''
        Add position to the pos_list at a specific time-step
        params:
        pos : A tuple (x, y)
        index : time-step
        '''
        assert(index not in self.node_pos_list)
        self.node_pos_list[index] = pos

    def printNode(self):
        '''
        Print function for the node
        For debugging purposes
        '''
        print('Node type:', self.node_type, 'with ID:', self.node_id, 'with positions:', self.node_pos_list.values(), 'at time-steps:', self.node_pos_list.keys())


class ST_EDGE():

    def __init__(self, edge_type, edge_id, edge_pos_list):
        '''
        Inititalizer function for the ST edge class
        params:
        edge_type : Type of the edge (Human-Human or Human-Obstacle)
        edge_id : Tuple (or set) of node IDs involved with the edge
        edge_pos_list : Positions of the nodes involved with the edge
        '''
        self.edge_type = edge_type
        self.edge_id = edge_id
        self.edge_pos_list = edge_pos_list

    def getPositions(self, index):
        '''
        Get Positions of the nodes at time-step index in the sequence
        params:
        index : time-step
        '''
        assert(index in self.edge_pos_list)
        return self.edge_pos_list[index]

    def getType(self):
        '''
        Get edge type
        '''
        return self.edge_type

    def getID(self):
        '''
        Get edge ID
        '''
        return self.edge_id

    def addPosition(self, pos, index):
        '''
        Add a position to the pos_list at a specific time-step
        params:
        pos : A tuple (x, y)
        index : time-step
        '''
        assert(index not in self.edge_pos_list)
        self.edge_pos_list[index] = pos

    def printEdge(self):
        '''
        Print function for the edge
        For debugging purposes
        '''
        print('Edge type:', self.edge_type, 'between nodes:', self.edge_id, 'at time-steps:', self.edge_pos_list.keys())

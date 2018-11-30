import networkx as nx
from anytree import Node, LevelOrderIter, RenderTree
from nltk import ngrams

class PetriNetBuilder:
    '''
    Build a petri net from a process tree so that we can replay log on it
    '''

    def __init__(self, settings, cluster_id, tree):
        self.settings = settings
        self.cluster_id = cluster_id
        self.tree = tree
        self.pn = self.build_pn_from_process_tree()

    def boundaries_of_node(self, node):
        '''
        return a tuple (incoming, outgoing) given a node
        # There are four cases:
        #   1) the node is a task or a tau => the boundaries is the node itself (both incoming and outgoing)
        #   2) the node is an operator (xor, loop, and) => the boundaries is the node and the end, e.g.,, XOR, end_XOR
        #   3) the node is a loop (xor, loop, and) => reversed of operator above
        #   4) the node is a sequence.
        '''
        if node.type == 'task' or node.type == 'tau' or node.type == 'tau-and' or node.type == 'place':
            return (node.shortname, node.shortname)

        elif node.type == 'Xor' or node.type == 'And':
            return (node.shortname, 'end_'+node.shortname)

        elif node.type == 'XorLoop':
            return ('end_'+node.shortname, node.children[2].shortname)

        elif node.type == 'Seq':
            # Link to first element of seq
            first = self.get_first_none_seq_nodes(node)
            boundaries_first = self.boundaries_of_node(first)[0]

            # Link to last element of seq
            last = self.get_first_none_seq_nodes(node, first=False)
            boundaries_last = self.boundaries_of_node(last)[1]
            return (boundaries_first, boundaries_last)
        else:
            exit('Types of nodes not supported (4): '+node.type)


    def get_first_none_seq_nodes(self, node, first=True):
        while node.type == 'Seq':
            if first:
                node = node.children[0]
            else:
                node = node.children[-1]
        return node

    def build_pn_from_process_tree(self):

        # We add a sequential operator at the top with a start and end activity below
        # the tree goes in the middle, it will force the BPMN to have a start and end node
        root = Node('Seq', shortname='[specialTOPseq]', type='Seq')
        Node('start', shortname='start', type='place', parent = root)
        self.tree.parent = root
        Node('end', shortname='end', type='place', parent = root)

        g = nx.DiGraph()
        def add_node(e, end=False):
            if not end:
                return g.add_node(e.shortname, shortname=e.shortname, type=e.type)
            else:
                return g.add_node('end_'+e.shortname, shortname='end_'+e.shortname, type=e.type)

        g.add_node('start', shortname='start', type='place', parent = root)
        g.add_node('end', shortname='end', type='place', parent = root)
        # Step 1: Add nodes + Transition
        for e in reversed([node for node in LevelOrderIter(root)]):
            if e.type == 'task' or e.type == 'tau' or e.type == 'tau-and':
                add_node(e)
            elif e.type == 'Xor' or e.type == 'XorLoop' or e.type == 'And':
                add_node(e)
                add_node(e, end=True)
            elif e.type == 'Seq' or e.type=='place':
                continue
            else:
                exit('Types of nodes not supported (1): '+e.type)


        # Step 2: Add edges (XOR)
        i = 0
        for e in reversed([node for node in LevelOrderIter(root) if node.type == 'Xor']):
            i += 1
            place_name = 'place_'+str(i)
            i += 1
            end_place_name = 'place_'+str(i)


            for child in e.children:
                # Add places
                edges = self.boundaries_of_node(child)
                g.add_node(place_name, shortname=place_name, type='place')
                g.add_node(end_place_name, shortname=end_place_name, type='place')
                g.add_edge(e.shortname, place_name)
                g.add_edge(place_name, edges[0])
                g.add_edge(edges[1], end_place_name)
                g.add_edge(end_place_name, 'end_'+e.shortname)

        # Step 2: Add edges (AND)
        for e in reversed([node for node in LevelOrderIter(root) if node.type == 'And']):

            for child in e.children:
                # Add places
                i += 1
                place_name = 'place_'+str(i)
                i += 1
                end_place_name = 'place_'+str(i)
                edges = self.boundaries_of_node(child)
                g.add_node(place_name, shortname=place_name, type='place')
                g.add_node(end_place_name, shortname=end_place_name, type='place')
                g.add_edge(e.shortname, place_name)
                g.add_edge(place_name, edges[0])
                g.add_edge(edges[1], end_place_name)
                g.add_edge(end_place_name, 'end_'+e.shortname)

        # Step 2: Add edges (SEQ)
        for e in [node for node in LevelOrderIter(root) if node.type == 'Seq']:

            for source, target in ngrams(e.children, 2):
                i += 1
                place_1 = 'place_'+str(i)
                g.add_node(place_1, shortname=place_1, type='place')
                source_node = self.boundaries_of_node(source)[1]
                target_node = self.boundaries_of_node(target)[0]
                g.add_edge(source_node, place_1)
                g.add_edge(place_1, target_node)

        # Remove place just after start
        after_start = list(g.out_edges('start'))[0][1]
        for after_after_start in g.out_edges(after_start):
            g.add_edge('start', after_after_start[1])
        g.remove_node(after_start)

        # Remove place just before end
        before_end = list(g.in_edges('end'))[0][0]
        for before_before_end in g.in_edges(before_end):
            g.add_edge(before_before_end[0], 'end')
        g.remove_node(before_end)

        # Step 2: Add edges LOOP)
        for e in ([node for node in LevelOrderIter(root) if node.type == 'XorLoop']):

            edges = self.boundaries_of_node(e.children[0])
            i += 1
            place_1 = 'place_'+str(i)
            g.add_node(place_1, shortname=place_1, type='place')
            i += 1
            place_2 = 'place_'+str(i)
            g.add_node(place_2, shortname=place_2, type='place')

            g.add_edge('end_'+e.shortname, place_1)    # end_[XorLoop0] --> 1
            g.add_edge(place_1, edges[0])    # end_[XorLoop0] --> 1
            g.add_edge(edges[1], place_2)           # 4 --> [XorLoop0]
            g.add_edge(place_2, e.shortname)           # 4 --> [XorLoop0]

            edges = self.boundaries_of_node(e.children[1])   #edges[0] = 5     //  edges[1] = 5      //  e.shortname = [XorLoop0]

            i += 1
            place_1 = 'place_'+str(i)
            g.add_node(place_1, shortname=place_1, type='place')
            i += 1
            g.add_edge(e.shortname, place_1)    # end_[XorLoop0] --> 5
            g.add_edge(place_1, edges[0])    # end_[XorLoop0] --> 5
            g.add_edge(e.shortname, place_1)           # 5 --> [XorLoop0]
            g.add_edge(place_1, e.children[2].shortname)           # 5 --> [XorLoop0]

            in_edges = []
            for in_edge in g.in_edges('end_'+e.shortname):
                in_edges.append(in_edge[0])

            for in_edge in in_edges:
                g.add_edge(edges[1], in_edge)

        return g

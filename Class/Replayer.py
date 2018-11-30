import networkx as nx
import pandas as pd
from anytree import LevelOrderIter, RenderTree, find


class Replayer:

    '''
    Manage the replay a log on a petri net
    '''
    def __init__(self, pnBuilder, tree, log, settings):
        self.settings = settings
        self.pnBuilder = pnBuilder
        self.pn = pnBuilder.pn
        self.tree = tree
        self.log = log
        self.tokens = set()
        self.counter = {}
        self.taskToAnd, self.andTaskToBranch, self.andBranchToTask, self.countOperatorPerBranch = self.linkTaskToAnd()
        self.nodeToLoop = self.linkNodeToLoop()
        self.nodeToXor = self.linkNodeToXor()
        self.visibleTasks = self.getVisibleTasks()
        self.nodeToIncrementLoop, self.nodeToIncrementLoop_inverse, self.nodeToLeaveLoop, self.nodeToLeaveLoop_inverse, self.dependentAndorXorLoop = self.linkNodeToIncrementLoop()
        self.traces_with_tau = self.replay(self.log.SequenceTxt)
        self.df = None
        self.abstract_df = None

    def linkTaskToAnd(self):
        '''
        Each task or tau is mapped to a list of and in which it is included:
        taskToAnd {'[tau10]': [], '[tau11]': [], '3': [], '[tau4]': ['[And2]'], '2': ['[And2]'], '[tau7]': ['[And2]'], '1': ['[And2]']}

        For each AND, we build a dictionary to know in which branch the task is
        For instance, below, 'tau4' and '2' belong to the same branch "0"
        This is the branch we insert in the matrix
        andTaskToBranch {'[And2]': {'[tau4]': 0, '2': 0, '[tau7]': 1, '1': 1}}

        For each AND, we build a dictionary to know which task or tau a branch have
        andBranchToTask {'[And2]': {0: ['[tau4]', '2'], 1: ['[tau7]', '1']}}
        '''
        taskToAnd = {}
        andTaskToBranch = {}
        andBranchToTask = {}
        for e in LevelOrderIter(self.tree):
            if e.type in ['tau','task']:
                taskToAnd[e.shortname] = []
                for above in e.path:
                    if above.type == 'And':
                        taskToAnd[e.shortname].append(above.shortname)

        for and_operator in LevelOrderIter(self.tree):
            if and_operator.type == 'And':
                andBranchToTask[and_operator.shortname] = {}
                for i_branch, branch in enumerate(and_operator.children):
                    andBranchToTask[and_operator.shortname][i_branch] = []
                    #if branch.type in ['task', 'tau']:
                    andBranchToTask[and_operator.shortname][i_branch].append(branch.shortname)

                    for descendant in branch.descendants:
                        #if descendant.type in ['task', 'tau']:
                        andBranchToTask[and_operator.shortname][i_branch].append(descendant.shortname)

        for and_operator, branchToTask in andBranchToTask.items():
            andTaskToBranch[and_operator] = {}
            for i_branch, tasks in branchToTask.items():
                for task in tasks:
                    andTaskToBranch[and_operator][task] = i_branch

        count_operator_per_branch = {}
        for and_operator, branchToTask in andBranchToTask.items():
            count_operator_per_branch[and_operator] = []
            for i_branch, tasks in branchToTask.items():
                count_operator_per_branch[and_operator].append(len(tasks))

        return taskToAnd, andTaskToBranch, andBranchToTask, count_operator_per_branch

    def linkNodeToLoop(self):
        '''
        Each node (e.g., task, tau, Xor) is mapped to a list of XorLoop in which it is included:
        {'[XorLoop0]': ['[XorLoop0]'], '[Seq1]': ['[XorLoop0]'], '[tau10]': ...

        :return:
        '''
        nodeToLoop = {}
        for e in LevelOrderIter(self.tree):
            nodeToLoop[e.shortname] = []
            for above in e.path:
                if above.type == 'XorLoop' and above != e:
                    nodeToLoop[e.shortname].append(above.shortname)
        return nodeToLoop

    def linkNodeToXor(self):
        '''
        Each node that appears after a XOR is link to the aformentioned XOR:
        e.g. {'[tau4]': '[Xor3]', '2': '[Xor3]', '[tau7]': '[Xor6]', '1': '[Xor6]'}

        :return:
        '''
        nodeToXor = {}
        for xor_operator in LevelOrderIter(self.tree):
            if xor_operator.type == 'Xor':
                place = list(self.pn.out_edges(xor_operator.shortname))[0][1]
                for _, after_xor in self.pn.out_edges(place):
                    nodeToXor[after_xor] = xor_operator.shortname
        return nodeToXor

    def linkNodeToIncrementLoop(self):
        '''
        A XorLoop will always have to exit edges, one for staying in the loop, one for incrementing the loop
        (correspond to child 1 and 2 of in the tree, the 0 being the loop itself)

        nodeToIncrementLoop record the nodes that are used to increment the loop.
        e.g., {'[tau10]': '[XorLoop0]'}

        Similarly, nodeToLeaveLoop record the nodes that are used to leave the loop
        {'[tau11]': '[XorLoop0]'}

        When we increment the loop, we would like to reset the counter of the nodes that are below in the tree
        Hence, we keep a list of the dependent nodes (they will be XorLoop or And)
        {'[XorLoop0]': ['[And2]']}

        :return:
        '''
        nodeToIncrementLoop = {}
        nodeToLeaveLoop = {}
        nodeToIncrementLoop_inverse = {}
        dependentAndorXorLoop = {}
        nodeToLeaveLoop_inverse = {}

        for xor_operator in LevelOrderIter(self.tree):
            if xor_operator.type == 'XorLoop':
                loopingNode = self.pnBuilder.boundaries_of_node(xor_operator.children[1]) # staying loop
                leavingNode = self.pnBuilder.boundaries_of_node(xor_operator.children[2]) # leaving loop
                nodeToIncrementLoop[loopingNode[0]] = xor_operator.shortname
                nodeToIncrementLoop_inverse[xor_operator.shortname] = loopingNode[0]
                nodeToLeaveLoop[leavingNode[0]] = xor_operator.shortname
                nodeToLeaveLoop_inverse[xor_operator.shortname] = leavingNode[0]
                dependentAndorXorLoop[xor_operator.shortname] = []
                for descendant in xor_operator.descendants:
                    if descendant.type in ['XorLoop', 'And']:
                        dependentAndorXorLoop[xor_operator.shortname].append(descendant.shortname)

        return nodeToIncrementLoop, nodeToIncrementLoop_inverse, nodeToLeaveLoop, nodeToLeaveLoop_inverse, dependentAndorXorLoop

    def getVisibleTasks(self):
        visibleTasks = set()
        for operator in LevelOrderIter(self.tree):
            if operator.type == 'task':
                visibleTasks.add(operator.shortname)
        return visibleTasks

    def reset(self):

        # Initialize tokens
        self.tokens = {'start'}

        # Initialize counters
        for e in LevelOrderIter(self.tree):
            if e.type in ['XorLoop','And']:
                self.counter[e.shortname] = 0

    def fire(self, node):
        missing_token_in_places = None

        # Check that all input places have a token
        for input in self.pn.in_edges(node['shortname']):
            node_before = self.pn.node[input[0]]
            if node_before['shortname'] not in self.tokens:
                missing_token_in_places = node_before['shortname']

        # No missing tokens, we can move all the tokens
        if missing_token_in_places is None:
            for input in self.pn.in_edges(node['shortname']):
                node_before = self.pn.node[input[0]]
                self.tokens.remove(node_before['shortname'])
            for output in self.pn.out_edges(node['shortname']):
                node_after = self.pn.node[output[1]]
                self.tokens.add(node_after['shortname'])


        return missing_token_in_places


    def replay(self, traces, completeTraces=True):
        traces_with_tau = []
        for i, trace in enumerate(traces):
            self.reset()
            trace = trace.split('-')
            if completeTraces:
                trace.append('end')

            full_path, missmatch = self.add_tau_activities(trace)

            traces_with_tau.append(full_path)

        return traces_with_tau


    def playing_token_game_until_firing_target(self, target, nodes_on_the_way, allow_task_not_observed, history_next_place):
        try:
            path = self.enumerate_potential_paths(target, allow_task_not_observed)
            for e in path:
                node = self.pn.node[e]

                if node['type'] == 'place':
                    continue

                missing_a_token_in_places = self.fire(node)

                if missing_a_token_in_places is None:
                    nodes_on_the_way.append(e)
                else:

                    next_node = self.enumerate_potential_paths(missing_a_token_in_places, allow_task_not_observed)[-2]

                    if next_node in history_next_place:
                        exit('token error: avoiding infinite loop...')

                    history_next_place.add(next_node)

                    nodes_on_the_way = self.playing_token_game_until_firing_target(next_node, nodes_on_the_way, allow_task_not_observed, history_next_place)
        except:
            pass
        return nodes_on_the_way

    def add_tau_activities(self, trace, allow_task_not_observed=False):
        '''
        :param trace: list of activities (only the visible one)
        :return: list of activities (including tau), None if the model does not match the trace
        '''
        full_path = []
        missmatch = False
        for task in trace:

            nodes_on_the_way = self.playing_token_game_until_firing_target(task, [], allow_task_not_observed, set())
            full_path.extend(nodes_on_the_way)

        return full_path, missmatch

    def filter_full_path(self, full_path):
        filtered = []
        for e in full_path:
            if self.pn.node[e]['type'] in ['tau','task']:
                filtered.append(e)

            if self.pn.node[e]['type'] in ['place']:
                node = find(self.tree, lambda node: node.name == e)
                if node.parent.type == ['Xor', 'XorLoop']:
                    filtered.append(e)


        return filtered

    def enumerate_potential_paths(self, target, allow_task_not_observed):
        potential_paths = []

        for token in self.tokens:
            if allow_task_not_observed:
                map = self.return_subgraph_allowing_only_tau_activity_and_task_itself(target)
            else:
                map = self.pn

            try:
                potential_paths.append(nx.shortest_path(map, token, target))
            except:
                pass

        if len(potential_paths) == 0:
            exit ('no path found')

        return sorted(potential_paths, key=len)[0]


    def return_subgraph_allowing_only_tau_activity_and_task_itself(self, task_to_keep):
        reduced_pn = self.pn.copy()
        for node in self.pn.nodes():
            n = self.pn.node[node]
            if n['type'] == 'task' and n['shortname'] != task_to_keep:
                reduced_pn.remove_node(node)


        return reduced_pn


    def build_matrix(self):
        features_continuous = []
        features_discrete = []
        for trace_with_tau in self.traces_with_tau:
            feature_continuous = {}
            feature_discrete = {}
            if trace_with_tau is not None:
                self.reset()
                for task in trace_with_tau:
                    self.manageCounter(task)
                    # Record and Increment And
                    if task in self.taskToAnd.keys():
                        for and_above in self.taskToAnd[task]:
                            feature_discrete.update(self.record(and_above, task))

                    # Record XOR
                    if task in self.nodeToXor.keys():
                        feature_discrete.update(self.record(self.nodeToXor[task], task))

                    # Leaving loop, recording...
                    if task in self.nodeToLeaveLoop.keys():
                        feature_continuous.update(self.record(self.nodeToLeaveLoop[task], task))

            features_continuous.append(feature_continuous)
            features_discrete.append(feature_discrete)

        discrete = pd.DataFrame(features_discrete, dtype="unicode")
        continuous = pd.DataFrame(features_continuous, dtype="int8")
        df = pd.concat([continuous, discrete], axis=1)

        start_cols = set()
        for col in list(df.columns):
            start_cols.add(col.split('|')[0])

        abstract_df = {}
        for start_col in start_cols:

            filter_cols = [col for col in df if col.startswith(start_col)]
            series = []
            for filter_col in filter_cols:
                series.append(df.loc[:,filter_col])

            abstract_df[start_col] = pd.concat(series)

        self.df = df
        self.abstract_df = abstract_df

    def manageCounter(self, task):

        # Record and Increment And
        if task in self.taskToAnd.keys():
            for and_above in self.taskToAnd[task]:
                self.counter[and_above] += 1

        # Incrementing Loop, and reset AND or XORLOOP counter below
        if task in self.nodeToIncrementLoop.keys():
            self.counter[self.nodeToIncrementLoop[task]] += 1

            for dependent in self.dependentAndorXorLoop[self.nodeToIncrementLoop[task]]:
                self.counter[dependent] = 0

    def record(self, operator, task):
        value = None
        if operator[1:4] == 'And':
            value = self.andTaskToBranch[operator][task]

        if operator[1:8] == 'XorLoop':
            value = self.counter[operator]

        elif operator[1:4] == 'Xor':
            value = task

        return {self.feature_name(operator, 'replay'): value}

    def feature_name(self, operator, type):
        '''

        :param operator:
        :param type: 'Replay', 'pf', 'pf+'
        :param next:
        :return:
        '''
        feature_name = operator
        if operator[1:4] == 'And':
            counter = self.counter[operator]
            if type in ['pf+', 'pf']:
                counter += 1
            feature_name = feature_name + '(' + str(counter) + ')'

        if type in ['pf+', 'replay']:
            feature_name = feature_name + '|'

            for loop_above in self.nodeToLoop[operator]:
                counter = self.counter[loop_above]
                feature_name = feature_name + loop_above + '{'+ str(counter) +'}'

        return feature_name






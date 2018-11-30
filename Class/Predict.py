from anytree import RenderTree, PreOrderIter, find_by_attr, find
import itertools
import pandas as pd

class Predict:
    '''
    We play a prefix using the replayer.
    Then, the class "Predict" takes the relay and predict the most likely way the tokens will be played until the end of the process
    '''
    def __init__(self, replayer, tree, pnBuilder, settings):
        self.settings = settings
        self.tree = tree
        self.replayer = replayer
        self.pnBuilder = pnBuilder
        self.pn = pnBuilder.pn
        self.guessed_activities = []
        self.stat_about_prediction_type = {'pf+':0, 'pf':0, 'first':0}

    def guess_suffix(self, prefix):
        self.guessed_activities = []
        traces_with_tau = self.replayer.replay(prefix, False)

        [self.replayer.manageCounter(t) for t in traces_with_tau[0]]

        activeTransitions = self.listActiveTransitions()
        transition = self.chooseTransition(activeTransitions)

        visible_activity = []
        if transition is not None:
            self.play_suffix(transition)
            if transition in self.replayer.visibleTasks:
                visible_activity.append(transition)

        return visible_activity

    def play_suffix(self, transition):
        if transition is None:
            return None
        if transition in self.replayer.visibleTasks:
            self.guessed_activities.append(transition)

        for token in self.pn.in_edges(transition):
            token = token[0]
            if token in self.replayer.tokens:
                self.replayer.tokens.remove(token)

        for out_edges in self.pn.out_edges(transition):
            out_edges = out_edges[1]
            self.replayer.tokens.add(out_edges)

        if self.replayer.tokens != {'end'}:
            activeTransitions = self.listActiveTransitions()
            transition = self.chooseTransition(activeTransitions)

            self.replayer.manageCounter(transition)
            self.play_suffix(transition)


        return transition


    def listActiveTransitions(self):
        # Remove token that are not active
        # a Token is not active if it points to a transition that have some empty places (missing token) coming in
        # Step 1: make a list of all transition that have a token pointing to them
        transitions = set()
        for token in self.replayer.tokens:
            for transition in self.pn.out_edges(token):
                transition = transition[1]
                activeTransition = True
                for incoming_in_transition in self.pn.in_edges(transition):
                    incoming_in_transition = incoming_in_transition[0]
                    if incoming_in_transition not in self.replayer.tokens:
                        activeTransition = False
                        break
                if activeTransition:
                    transitions.add(transition)

        return transitions

    def chooseTransition(self, activeTransition):
        if len(activeTransition) == 1:
            return list(activeTransition)[0]
        elif len(activeTransition) == 0:
            return None
        else:
            nodes_list = set()
            for transition in list(activeTransition):
                nodes_list.add(find(self.tree, lambda node: node.shortname == transition.replace('end_','')))

            nodes_list = list(nodes_list)

            score = []
            for node_1, node_2 in itertools.combinations(nodes_list, 2):
                score.append(self.highest_distinct_branch(node_1, node_2))


            score.sort(key=lambda t: t[1], reverse=True)

            node = score[0][0]

            if node.type == 'XorLoop':
                try:
                    try:
                        decision_to_stay_in_loop = self.choose_xorloop(node, 'pf+')
                        self.stat_about_prediction_type['pf+'] += 1
                    except:
                        decision_to_stay_in_loop = self.choose_xorloop(node, 'pf')
                        self.stat_about_prediction_type['pf'] += 1
                except:
                    decision_to_stay_in_loop = self.choose_xorloop(node, 'first')
                    self.stat_about_prediction_type['first'] += 1

                # Staying in loop
                if decision_to_stay_in_loop:
                    transition = self.replayer.nodeToLeaveLoop_inverse[node.shortname]
                else:
                    transition = self.replayer.nodeToIncrementLoop_inverse[node.shortname]

                activeTransition = self.remove_transition(transition, activeTransition)

            elif node.type == 'And':
                try:
                    try:
                        branch_to_keep = self.choose_and(node, activeTransition, 'pf+')
                        self.stat_about_prediction_type['pf+'] += 1
                    except:
                        branch_to_keep = self.choose_and(node, activeTransition, 'pf')
                        self.stat_about_prediction_type['pf'] += 1
                except:
                    branch_to_keep = self.choose_and(node, activeTransition, 'first')
                    self.stat_about_prediction_type['first'] += 1

                for branch, tasks in self.replayer.andBranchToTask[node.shortname].items():
                    if branch != branch_to_keep:
                        for task in tasks:
                            activeTransition = self.remove_transition(task, activeTransition)

            elif node.type == 'Xor':
                try:
                    try:

                        top_value = self.choose_xor(node, 'pf+')
                        self.stat_about_prediction_type['pf+'] += 1
                    except:

                        top_value = self.choose_xor(node, 'pf')
                        self.stat_about_prediction_type['pf'] += 1
                except:
                    top_value = self.choose_xor(node, 'first')
                    self.stat_about_prediction_type['first'] += 1

                place = list(self.pn.out_edges(node.shortname))[0]
                for children in self.pn.out_edges(place):
                    children = children[1]
                    if children != top_value:
                        activeTransition = self.remove_transition(children, activeTransition)

            else:
                exit('not prepared for this: '+node.type)

            return self.chooseTransition(activeTransition)

    def remove_transition(self, to_remove, activeTransitions):
        if to_remove in activeTransitions:
            activeTransitions.remove(to_remove)
        if 'end_'+to_remove in activeTransitions:
            activeTransitions.remove('end_'+to_remove)

        return activeTransitions

    def choose_xorloop(self, node, type):
        if type in ['pf+','pf']:
            current = self.replayer.counter[node.shortname]
            feature_name = self.replayer.feature_name(node.shortname, type)

            if type == 'pf+':
                column = self.replayer.df.loc[:, feature_name]

            elif type == 'pf':
                column = self.replayer.abstract_df[feature_name]

            return column.median() > current

        else:
            # If not sure, leave the loop
            return False

    def choose_xor(self, node, type):
        if type in ['pf+','pf']:
            feature_name = self.replayer.feature_name(node.shortname, type)
            if type == 'pf+':
                column = self.replayer.df.loc[:, feature_name]
            elif type == 'pf':
                column = self.replayer.abstract_df[feature_name]

            return column.value_counts().index[0]

        else:
            place = list(self.pn.out_edges(node.shortname))[0]
            return list(self.pn.out_edges(place))[0]

    def choose_and(self, node, activeTransition, type):
        if type in ['pf+', 'pf']:
            feature_name = self.replayer.feature_name(node.shortname, type)

            if type == 'pf+':
                column = self.replayer.df.loc[:, feature_name]
            else:
                column = self.replayer.abstract_df[feature_name]

            branches = column.value_counts().index
            branch_sorted = pd.Series(column.value_counts(sort=False).values).divide(self.replayer.countOperatorPerBranch[node.shortname]).sort_values(ascending=False)
            branch_to_keep = None
            for i in branch_sorted.index:
                branch_to_keep = branches[i]
                under_branch = set(self.replayer.andBranchToTask[node.shortname][branch_to_keep])

                if len(under_branch.intersection(activeTransition))==0:
                    branch_to_keep = None
                else:
                    break

            if branch_to_keep == None:
                exit('Not enought results for prediction')
        elif type == 'first':
            branch_to_keep = None
            for potential_transition, branch in self.replayer.andTaskToBranch[node.shortname].items():
                if potential_transition in activeTransition:
                    branch_to_keep = branch
                    break
                if 'end_'+potential_transition in activeTransition:
                     branch_to_keep = branch
                     break
            if branch_to_keep is None:
                exit('error while choosing the first AND')

        else:
            exit('to be implemented')

        return branch_to_keep

    def highest_distinct_branch(self, node_1, node_2):
        path_1 = node_1.path
        path_2 = node_2.path
        for level, _ in enumerate(path_1):
            if path_1[level] != path_2[level]:
                return (path_1[level-1], level)


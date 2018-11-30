from anytree import RenderTree, PreOrderIter
from Class.MineProcessTree import MineProcessTree
from Class.Replayer import Replayer
from Class.Predict import Predict
from Class.PetriNetBuilder import PetriNetBuilder

class Orchestration:
    '''
    Orchestratation of the replay
    '''

    def __init__(self, cluster_id, xes_file_name, length, settings, train):
        self.length = length
        self.settings = settings
        self.cluster_id = cluster_id
        self.xes_file_name = xes_file_name
        self.train = train
        self.tree = self.build_tree()
        self.pnBuilder = PetriNetBuilder(self.settings, self.cluster_id, self.tree)
        self.replayer = None
        self.predictor = None

        self.replayLog(train)
        self.build_predictor()

    def build_task_list(self):
        tasks = set()
        for operator in PreOrderIter(self.tree):
            if operator.type == 'task':
                tasks.add(operator.shortname)
        return tasks

    def build_tree(self):
        pt = MineProcessTree(self.length, self.cluster_id, self.settings, self.xes_file_name)
        return pt.parseTree()

    def replayLog(self, log):
        self.replayer = Replayer(self.pnBuilder, self.tree, log, self.settings)
        self.replayer.build_matrix()

    def predict(self, prefix):
        self.predictor.guess_suffix(["-".join(prefix)])
        return self.predictor.guessed_activities

    def build_predictor(self):
        self.predictor = Predict(self.replayer, self.tree, self.pnBuilder, self.settings)

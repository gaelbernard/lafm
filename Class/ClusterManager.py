from multiprocessing.dummy import Pool as ThreadPool
from utils.CSVtoXES import CSVtoXES
from Class.DiscoverProcessTrees import DiscoverProcessTrees
from Class.Cluster import Cluster
from Class.Orchestration import Orchestration
from utils.DistanceDiscreteEvents import DistanceDiscreteEvents
import pandas as pd
import operator

class ClusterManager:
    '''
    Manage the lafm process for each cluster:
    i.e., discovering process tree, replaying event log, evaluate quality of the prediction for the test data set
    '''
    def __init__(self, settings, log, csv, datapreparation):
        self.clusters = {}
        self.settings = settings
        self.datapreparation = datapreparation
        self.cluster_sizes = list(range(2, settings['value_max_of_min_cluster_to_test']))
        self.log = log
        self.xes_folder = None
        self.csv = csv
        self.orchestrations = {}
        self.tread = 10

    def createCluster(self):
        pool = ThreadPool(self.tread)
        self.clusters = dict(zip(self.cluster_sizes, pool.map(self.pool_cluster, self.cluster_sizes)))
        pool.close()
        delete_clusters = set()

        for cluster_id, cluster in self.clusters.items():
            if len(cluster.clusters) <= 1:
                delete_clusters.add(cluster_id)

        for del_cluster in delete_clusters:
            self.cluster_sizes.remove(del_cluster)
            del self.clusters[del_cluster]

        for cluster_id, cluster in self.clusters.items():
            cases_id_build_set = set()
            cases_id_training_set = set()
            for c in cluster.clusters.values():
                cases_id_build_set = cases_id_build_set.union(c['cases_id_build_set'])
                cases_id_training_set = cases_id_training_set.union(c['cases_id_training_set'])
            cases_id_build_set = len(cases_id_build_set)
            cases_id_training_set = len(cases_id_training_set)

    def pool_cluster(self, min_e_per_cluster):
        cluster = Cluster(self.csv.train['SequenceTxt'], min_e_per_cluster, self.settings, self.datapreparation)
        return cluster

    def createFiles(self, xes_folder):
        pool = ThreadPool(self.tread)
        self.xes_folder = xes_folder
        pool.map(self.pool_createFiles, self.cluster_sizes)
        pool.close()

    def pool_createFiles(self, min_e_per_cluster):
        for cluster_id, cluster_content in self.clusters[min_e_per_cluster].clusters.items():
            CSVtoXES(self.xes_folder + '/' + str(min_e_per_cluster) + '_' + str(cluster_id) + '.xes', self.csv.train.loc[cluster_content['cases_id_build_set']]).write_xes()

    def discoverTrees(self, names):
        DiscoverProcessTrees(self.settings).mineTree(names)

    def parseTrees(self):
        for min_e_per_cluster in self.cluster_sizes:
            for cluster_id, cluster_content in self.clusters[min_e_per_cluster].clusters.items():
                name_cluster = str(min_e_per_cluster) + '_' + str(cluster_id)
                self.orchestrations[name_cluster] = Orchestration(cluster_id, name_cluster, 0, self.settings, self.csv.train.loc[cluster_content['cases_id_training_set']])

    def replayer(self):
        pool = ThreadPool(self.tread)
        hyper_distances = dict(zip(self.cluster_sizes, pool.map(self.pool_replayer, self.cluster_sizes)))
        pool.close()
        best_min_size = max(hyper_distances.items(), key=operator.itemgetter(1))[0]
        return best_min_size

    def pool_replayer(self, min_e_per_cluster):
        distances = []
        i = 0
        for index, t in self.csv.hyper.iterrows():

            if i % 200 == 0:
                print('replay:', min_e_per_cluster, '     iteration,', i, 'on', self.csv.hyper.shape[0])
            i += 1

            best_cluster_id = 0
            if len(self.clusters[min_e_per_cluster].clusters) > 1:
                best_cluster_id = self.clusters[min_e_per_cluster].predict_cluster_using_classifier(['-'.join(t['prefix'])])

            name_cluster = str(min_e_per_cluster) + '_' + str(best_cluster_id)
            self.orchestrations[name_cluster].predict(t['prefix'])
            dist = DistanceDiscreteEvents(self.orchestrations[name_cluster].predictor.guessed_activities, t['suffix'])
            distances.append(dist.damerau())

        return pd.Series(distances).mean()

import pandas as pd
import hdbscan
import numpy as np
from sklearn.linear_model import SGDClassifier
from numpy.random import RandomState

class Cluster:
    '''
    Cluster traces prepared in datapreparation (ngrams) using hdbscan.
    It also train a classifier that trains, for each prefix length,
    to predict in which cluster a trace will be assigned so it can
    be reused when predicting a prefix.
    '''
    def __init__(self, sequences, min_size_cluster, settings, datapreparation):

        self.settings = settings
        self.prob = (settings['prob_building'],settings['prob_training'])
        self.min_size_cluster = min_size_cluster
        self.datapreparation = datapreparation
        self.clusterer = hdbscan.HDBSCAN(min_cluster_size=min_size_cluster, allow_single_cluster=False, prediction_data=True, cluster_selection_method="eom")
        self.seq = sequences
        self.max_len_seq = sequences.str.split('-',expand=True).shape[1]
        self.cluster_labels = None
        self.clusters = self.build_cluster()
        if len(self.clusters)>1:
            self.classifiers = self.train_classifier()

    def __str__(self):
        output = ""
        for cluster_id, cluster_content in self.clusters.items():
            output += 'CLUSTER ID '+str(cluster_id)+ '  size build:'+ str(len(cluster_content['cases_id_build_set']))+ '  size training:'+str(len(cluster_content['cases_id_training_set']))
        return output

    def train_classifier(self):
        '''
        train a classifier for each prefix length.
        For instance, if abcd is assigned to cluster 4, we train
        - the classifier[1] that 'a'=>4
        - the classifier[2] that 'ab'=>4
        - the classifier[2] that 'abc'=>4
        - the classifier[2] that 'abcd'=>4
        :return: dict where key is the length
        '''
        classifiers = {}
        for length in self.datapreparation.count_matrix_per_length.keys():
            label = pd.Series(self.cluster_labels)
            label = label[label != -1]
            classifiers[length] = SGDClassifier(n_jobs=1, tol=0.1)
            label_to_keep = label[label.notnull()]
            classifiers[length].fit(self.datapreparation.count_matrix_per_length[length].iloc[label_to_keep.index].loc[label.index.values,:].values,label_to_keep.values)
        return classifiers

    def build_cluster(self):

        # Check if we use SVD (dimensionality reduction technique)
        if self.datapreparation.svd != None:
            X = self.datapreparation.svd.transform(self.datapreparation.count_matrix)
        else:
            X = self.datapreparation.count_matrix

        # Add a (very) small amount of noise  (otherwise hdbscan complains)
        prng = RandomState()
        X = X + (prng.rand(X.shape[0], X.shape[1])/10**10)

        # Cluster!
        self.clusterer.fit_predict(X)

        clusters = {}
        soft_clusters = pd.DataFrame(hdbscan.all_points_membership_vectors(self.clusterer)) # Soft clustering (used to find strong and weak representatives)
        self.cluster_labels = soft_clusters.idxmax(axis=1) # Hard clustering (used for the classifier)

        for cluster_id in range(soft_clusters.shape[1]):
            prob_c = soft_clusters.loc[:,cluster_id]
            clusters[cluster_id] = {}
            build = list(prob_c[prob_c >= self.prob[0]].index)
            build = self.seq.iloc[build].drop_duplicates(keep='first', inplace=False)
            clusters[cluster_id]['cases_id_build_set'] = list(build.index) # Strong representative (e.g., 80% sure the traces is in the cluster)
            clusters[cluster_id]['cases_id_training_set'] = list(self.seq.iloc[list(prob_c[prob_c >= self.prob[1]].index)].index)  # Weak representative (e.g., 20% sure the traces is in the cluster)
            if len(clusters[cluster_id]['cases_id_build_set']) == 0:
                clusters[cluster_id]['cases_id_build_set'] = list(self.seq.iloc[[prob_c.idxmax()]].index)
            if len(clusters[cluster_id]['cases_id_training_set']) == 0:
                clusters[cluster_id]['cases_id_training_set'] = list(self.seq.iloc[[prob_c.idxmax()]].index)
        return clusters


    def predict_cluster_using_classifier(self, prefix):
        '''
        Given a prefix of event, return the most probable cluster id
        :param prefix: list of events e.g., ['a','b','c']
        :return: if of the cluster
        '''

        if len(prefix[0].split('-')) in self.datapreparation.count_matrix_per_length.keys():
            length = len(prefix[0].split('-'))
        else:
            length = self.max_len_seq

        dist_m_prefix = self.datapreparation.cv.transform(prefix)

        if self.datapreparation.svd != None:
            return self.classifiers[length].predict(self.datapreparation.svd.transform(dist_m_prefix))[0]
        else:
            return self.classifiers[length].predict(dist_m_prefix)[0]

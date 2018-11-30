from Class.CSVParser import CSVParser
from scipy import stats
from Class.ClusterManager import ClusterManager
from Class.DataPreparation import DataPreparation
from utils.DistanceDiscreteEvents import DistanceDiscreteEvents
from utils.Utils import Utils
import pandas as pd
import time

final_report = []
folder_name = str(time.strftime("%Y-%m-%dat%H-%M-%S"))+'/'
settings = {
    'base_folder' : '/Users/gbernar1/Dropbox/PhD_cloud/01-Research/02-present/Customer_Journey_Mapping/14_prediction/07-correctionTreeReplayer/processTreePredictor2/',                         # Current Folder
    'dataset' : 'data/round 3 treeSeed 1.xes.csv',  # Relative path to dataset (from base_folder)
    'CV_ngrams_min' : 1,                            # minimum number of char in the ngrams for the Count Vectorizer
    'CV_ngrams_max' : 2,                            # maximum number of char in the ngrams for the Count Vectorizer
    'value_max_of_min_cluster_to_test' : 11,        # HDBSCAN takes as argument the minimum number of element per cluster.
                                                    # We do a hyperparameter from 2 to {value_max_of_min_cluster_to_test}
    'ratio_validation' : 0.1,                       # {ratio_validation} of the training set is used for the hyperparameter search
    'svd_n_components' : 200,                       # Desired dimensionality of output data for SVD
    'prob_building' : 0.8,                          # Traces should have a probability > {prob_building} to be used by the inductive miner
    'prob_training' : 0.2,                          # Traces should have a probability > {prob_training} to appear in LaFM (hence be replayed)
    'folder_name' : folder_name                     # Name of the folder that will be created
}

# Folder management (create a folder to store the results)
xes_folder = settings['base_folder'] + 'xes_temp/' + settings['folder_name']
xes_folder_output = settings['base_folder'] + 'xes_temp_output/' + settings['folder_name']
results_folder = settings['base_folder'] + 'results/' + settings['folder_name']
for dir in [xes_folder, xes_folder_output, results_folder]:
    Utils().create_empty_folder(dir)

# Load CSV
csv = CSVParser(settings['base_folder']+settings['dataset'], 'CaseID', 'ActivityID', settings)
log = csv.parse_traces()

# Split
csv.split_test_set(log)
csv.hyperparameter_set() # {ratio_validation} of the training set is cut for the hyperparater search

if csv.test.shape[0] == 0:
    exit('empty event log')

# Extract feature (count ngrams)
datapreparation = DataPreparation(settings, csv)

# Create orchestrator (used to replay traces)
orchestrations = {}

# Cluster Manager manage all the clusters
clusterManager = ClusterManager(settings, log, csv, datapreparation)
clusterManager.createCluster()
clusterManager.createFiles(xes_folder)

names = []
for cluster_id, c_content in clusterManager.clusters.items():
    for n_cluster in range(len(c_content.clusters)):
        names.append(str(cluster_id)+'_'+str(n_cluster)+'.xes.txt')

clusterManager.discoverTrees(names)
clusterManager.parseTrees()
best_min_size = clusterManager.replayer() # Selection of the best min size (min number of element in cluster used by hdbscan)
cluster = clusterManager.clusters[best_min_size]
orchestrations = clusterManager.orchestrations



distances = []
report = []
for index, t in csv.test.iterrows():

    prefix_txt = '-'.join(t['prefix'])

    # Get the best cluster's name
    best_cluster_id = cluster.predict_cluster_using_classifier([prefix_txt])
    name_cluster = str(best_min_size) + '_' + str(best_cluster_id)

    # Make a prediction given a prefix
    orchestrations[name_cluster].predict(t['prefix'])

    # Measure the distance between the predicted suffix and the ground truth (suffix)
    dist = DistanceDiscreteEvents(orchestrations[name_cluster].predictor.guessed_activities, t['suffix'])
    dist_damereau, dist_levenshtein = dist.damerau(), dist.levenshtein()
    distances.append(dist_damereau)

    # Adding the results in the report...
    report.append({'NUM_prefix': t['prefix'], 'STR_prefix': prefix_txt, 'NUM_suffix_guessed':orchestrations[name_cluster].predictor.guessed_activities, 'NUM_suffix':t['suffix'], 'DIST_damerau_levenshtein_distance':dist_levenshtein, 'DIST_levenshtein_distance':dist_damereau, 'min_e_per_cluster':best_min_size})

    # Show progress
    if index % 200 == 0:
        print(index, stats.describe(distances))

# Write the report in a csv file
pd.DataFrame(report).to_csv(results_folder+'lines.csv')

final_output = {
    'test.shape':str(csv.test.shape[0]),
    'train.shape':str(csv.train.shape[0]),
    'dataset':settings['dataset'],
    'folder_name':settings['folder_name'],
    'num_clusters':len(cluster.clusters),
    'mean':pd.Series(distances).mean(),
    'stats':str(stats.describe(distances)),
}
final_report.append({**settings, **final_output})
pd.DataFrame({**settings, **final_output}, index=[0]).to_csv(results_folder+'report.csv')
pd.DataFrame(final_report).to_csv('results/'+folder_name[:-1]+'.csv')

print('FINAL: {0}, REPORTS AVAILABLE IN:{1}'.format(stats.describe(distances), folder_name[:-1]))


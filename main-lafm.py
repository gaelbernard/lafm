from Class.CSVParser import CSVParser
from utils.CSVtoXES import CSVtoXES
from scipy import stats
from Class.Orchestration import Orchestration
from Class.DiscoverProcessTrees import DiscoverProcessTrees
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
    'svd_n_components' : 200,                       # Desired dimensionality of output data for SVD
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

# split training test
csv.split_test_set(log)
if csv.test.shape[0] == 0:
    exit('empty event log')

# Extract feature (count ngrams)
datapreparation = DataPreparation(settings, csv)

# Variable below are hardcoded to zero (but not in the clustered version of lafm, clafm)
best_cluster_id, min_e_per_cluster, cluster_id, best_min_size = 0, 0, 0, 0
CSVtoXES(xes_folder + '/' + str(min_e_per_cluster) + '_' + str(cluster_id) + '.xes', csv.train).write_xes()

# Discover the process tree using Prom
DiscoverProcessTrees(settings).mineTree([str(best_min_size)+'_'+str(cluster_id)+'.xes.txt'])

# Create orchestrator (used to replay traces)
name_file = str(min_e_per_cluster) + '_' + str(cluster_id)
orchestration = Orchestration(cluster_id, name_file, 0, settings, csv.train)

# Storing the results in a list (later transformed in pandas df and exported as csv)
distances = []
report = []
for index, t in csv.test.iterrows():

    prefix_txt = '-'.join(t['prefix'])

    # Make a prediction given a prefix
    orchestration.predict(t['prefix'])

    # Measure the distance between the predicted suffix and the ground truth (suffix)
    dist = DistanceDiscreteEvents(orchestration.predictor.guessed_activities, t['suffix'])
    dist_damereau, dist_levenshtein = dist.damerau(), dist.levenshtein()
    distances.append(dist_damereau)

    # Adding the results in the report...
    report.append({'NUM_prefix': t['prefix'], 'STR_prefix': prefix_txt, 'NUM_suffix_guessed':orchestration.predictor.guessed_activities, 'NUM_suffix':t['suffix'], 'DIST_damerau_levenshtein_distance':dist_levenshtein, 'DIST_levenshtein_distance':dist_damereau, 'min_e_per_cluster':best_min_size})

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
    'mean':pd.Series(distances).mean(),
    'stats':str(stats.describe(distances)),
}
final_report.append({**settings, **final_output})

pd.DataFrame({**settings, **final_output}, index=[0]).to_csv(results_folder+'report.csv')
pd.DataFrame(final_report).to_csv('results/'+folder_name[:-1]+'.csv')

print('FINAL: {0}, REPORTS AVAILABLE IN:{1}'.format(stats.describe(distances), folder_name[:-1]))
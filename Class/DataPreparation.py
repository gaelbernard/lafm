from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
import pandas as pd

class DataPreparation:
    def __init__(self, settings, csv):
        '''
        Extract features from a CSV using CountVectorizer for all prefix length
        '''

        self.seq = csv.train['SequenceTxt']
        self.settings = settings
        self.cv = CountVectorizer(max_features=100000, ngram_range=(settings['CV_ngrams_min'],settings['CV_ngrams_max']), token_pattern='[0-9]+', binary=True)
        self.svd = TruncatedSVD(n_components=settings['svd_n_components'])
        self.csv = csv
        self.max_len_seq = self.seq.str.split('-', expand=True).shape[1]

        count_matrix = self.cv.fit_transform(self.seq)
        self.count_matrix = pd.DataFrame(count_matrix.A, columns=self.cv.get_feature_names())
        try:
            self.svd.fit(self.count_matrix)
        except ValueError:
            self.svd = None

        self.count_matrix_per_length = {}
        self.get_count_matrix_per_length()

    def get_count_matrix_per_length(self):
        for length in range(2,self.max_len_seq+1):

            seq_cut = self.seq.str.replace('-','-=').str.split('-', expand=True).iloc[:,0:length].astype(str).sum(axis=1).str.replace('None','').str.replace('=','-')
            c_matrix = self.cv.transform(seq_cut)
            if self.svd != None:
                self.count_matrix_per_length[length] = pd.DataFrame(self.svd.transform(c_matrix))
            else:
                self.count_matrix_per_length[length] = pd.DataFrame(c_matrix.toarray())
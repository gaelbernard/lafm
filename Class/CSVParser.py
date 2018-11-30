import pandas as pd
import math

class CSVParser:

    def __init__(self, path, case_column, activity_column, settings):
        '''
        Read a csv file and load it in a pandas dataframe
        :param path: path to the file
        :param case_column: column that indicates the trace_id
        :param activity_column: column that indicates the activity
        :param settings: dictionary
        '''
        self.settings = settings
        self.path = path
        self.case_column = case_column
        self.activity_column = activity_column
        self.train = None
        self.test = None
        self.hyper = None
        if path is not '':
            self.csv_pandas = self.load_csv()

    def load_csv(self):
        return pd.read_csv(self.path)

    def parse_traces(self):

        # Isolate the columns case_id and activity_id
        s = self.csv_pandas.loc[:,[self.case_column, self.activity_column]]

        # Force the column to be of type string (otherwise the concatenation does not work)
        s[self.activity_column] = s[self.activity_column].astype(str)

        # For each traces, concatenate the activity; e.g., 1=>1-2-1, 2=>1-3-3-3-4-1, 3=>1-2-1
        s = s.groupby(self.case_column)[self.activity_column].apply(lambda x: "-".join(x)).to_frame()
        s.columns = ['SequenceTxt']

        s['SequenceTxt'] = s['SequenceTxt']

        return s

    def split_test_set(self, s):
        nb_train = (int(math.ceil(s.shape[0]/3)))
        train = s.head(nb_train*2)
        test = s.tail(s.shape[0]-train.shape[0])
        test_row = []
        for case_id, seq in test.iterrows():
            seq = seq['SequenceTxt'].split('-')
            for length in range(len(seq)):
                if length<2:
                    continue
                if length == len(seq):
                    continue
                prefix = seq[0:length] #length, case_id
                suffix = seq[length:] #length, case_id
                test_row.append({'prefix':prefix, 'suffix':suffix, 'length':length, 'case_id':case_id})

        test = pd.DataFrame(test_row)
        index_not_null = train['SequenceTxt'].str.split('-',expand=True)[1].notnull()
        self.train = train.loc[index_not_null,:]
        self.test = test
        return train, test

    def hyperparameter_set(self):
        row = []
        sub = self.train.sample(frac=self.settings['ratio_validation'], random_state=1)
        self.train = self.train.loc[~self.train.index.isin(sub.index)]

        for k, s in sub.iterrows():
            seq = s['SequenceTxt'].split('-')
            for length in range(2, len(seq)):

                prefix = seq[:length]
                rest = len(seq)-length
                if rest == 0:
                    suffix = []
                else:
                    suffix = seq[-rest:]

                row.append({'prefix': prefix, 'suffix': suffix, 'length': length, 'case_id': k})

        self.hyper = pd.DataFrame(row)


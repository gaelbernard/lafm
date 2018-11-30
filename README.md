# LaFM and c-LaFM

LaFM and c-LaFM is a path prediction algorithm. For instance, given the prefix ['a','b','c'] the algorithm predicts the remaining path (e.g., ['d','d','e']) by learning from a set of event logs (e.g., ['a','b','c','d','d','e], ['a','b','c','d','d','e'], [b','c','d','d','e','z']]). More details in the paper [currently under review].

## Getting Started

The algorithm takes as input a CSV file where each line is an event. It should contain:
 - a column named *CaseID* which allows to glue together events from the same trace
 - a column named *ActivityID* which is the activity itself that we are trying to predict.

 For instance, the csv below correspond to 2 traces: ['1','2','3'] ['7','6','6','7']
 ```
CaseID,ActivityID
0,1
0,2
1,7
0,3
2,6
3,6
4,7
```

## LaFM vs. c-LaFM
LaFM performs well with datasets without noise (typically synthetic datasets).
When the dataset is complex (typically real life datasets), c-LaFM will work better because it includes a clustering step.

The difference is that c-LaFM cluster the traces. Then a prediction model is learnt for each clusters.

### Prerequisites
LaFM and c-LAFM are using the inductive miner from ProM (through the commmand line interface). Hence, you should follow the instruction in the folder "prom/" prior to run the algorithms.

### Running the algorithm
LaFM is run within main-lafm.py while c-LaFM is run using main-clafm.py. The dict "settings" at the top of both files should be self explanatory. By default the parameters are the same as used in the paper [currently under review]. The results are stored in the folder "results/" while temporary files created during the process (e.g., process trees) are available in the folders "xes_temp" and "xes_temp_output".

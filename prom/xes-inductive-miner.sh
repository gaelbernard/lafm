String base_folder = "/Users/gbernar1/Dropbox/PhD_cloud/01-Research/02-present/Customer_Journey_Mapping/14_prediction/07-correctionTreeReplayer/processTreePredictor2/";

File timeNow = new File(base_folder+"current_file/");
File[] timeNows = timeNow.listFiles();
String timeNowName = "";
for (int i = 0; i < timeNows.length; i++) {
  if (timeNows[i].isFile()) {
	   timeNowName = timeNows[i].getName()+'/';
  } 
}
File tdl = new File(base_folder+"current_file/"+timeNowName);
tdl.delete();
File folder = new File(base_folder+"xes_temp/"+timeNowName);
File[] listOfFiles = folder.listFiles();

for (int i = 0; i < listOfFiles.length; i++) {
  if (listOfFiles[i].isFile()) {
    log = open_xes_log_file(base_folder+"xes_temp/"+timeNowName+listOfFiles[i].getName());
	org.deckfour.xes.info.XLogInfo logInfo = org.deckfour.xes.info.XLogInfoFactory.createLogInfo(log);
	org.deckfour.xes.classification.XEventClassifier classifier = logInfo.getEventClassifiers().iterator().next();
	org.processmining.plugins.InductiveMiner.mining.MiningParameters parameters = new org.processmining.plugins.InductiveMiner.mining.MiningParametersIM();
	parameters.setNoiseThreshold((float) 0.0);
	process_tree_0 = mine_process_tree_with_inductive_miner_with_parameters(log, parameters);
	PrintWriter writer = new PrintWriter(base_folder+"xes_temp_output/"+timeNowName+listOfFiles[i].getName()+".txt", "UTF-8");
	writer.println(process_tree_0);
	writer.close();
	
  } 
}

System.out.println("done");
System.exit(1);
return;

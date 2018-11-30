# Using ProM through the command line interface (CLI)

In order to use the inductive miner (transforming event logs to process trees) we use the CLI of ProM. It might be a bit cumberstone to install, do not hesitate to contact me in case you encounter any issues.

## Steps to follow

This blog post helps us in using the CLI of Prom: https://dirksmetric.wordpress.com/2015/03/11/tutorial-automating-process-mining-with-proms-command-line-interface/

1. Install ProM from http://www.promtools.org/doku.php (we used ProM 6.7). 
2. Adapt the path of the JAVABIN in "prom/ProM67cli.sh"
3. Adapt the path of the variable "base_folder" in the file "prom/xes-inductive-miner.sh" so that it points to the current folder from which the python file are executed (the one above main-lafm.py)
4. Put the files "prom/ProM67cli.sh" and "prom/xes-inductive-miner.sh" within the folder containing the installation of prom (Typically: /Applications/ProM-6.7.app/Contents/Resources/)
5. Adapt the command "self.cmd" in the class "Class/DiscoverProcessTrees" so that it points to the files you just moved in point 4 above (i.e., "ProM67cli.sh" "xes-inductive-miner.sh")

Done! It should work. If not, we encourage you to test the command following command in the terminal so that you can see the error logs.
 ```
/Applications/ProM-6.7.app/Contents/Resources/ProM67cli.sh -f /Applications/ProM-6.7.app/Contents/Resources/xes-inductive-miner.sh
 ```
 
 
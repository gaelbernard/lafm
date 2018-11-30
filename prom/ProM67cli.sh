#!/bin/sh

###
## ProM specific
###
PROGRAM=ProM
CP=./ProM67_dist/ProM-Framework.jar:./ProM67_dist/ProM-Contexts.jar:./ProM67_dist/ProM-Models.jar:./ProM67_dist/ProM-Plugins.jar
LIBDIR=./ProM67_lib
MAIN=org.processmining.contexts.cli.CLI 

####
## Environment options
###
JAVABIN=/Library/Java/JavaVirtualMachines/jdk1.8.0_121.jdk/Contents/Home/bin/Java

###
## Main program
###

add() {
	CP=${CP}:$1
}


for lib in $LIBDIR/*.jar
do
	add $lib
done

$JAVABIN -version
$JAVABIN -classpath ${CP} -da -Djava.library.path=${LIBDIR} -Djava.util.Arrays.useLegacyMergeSort=true -Xmx2G -XX:MaxPermSize=2048m -DsuppressSwingDropSupport=false ${MAIN} $1 $2


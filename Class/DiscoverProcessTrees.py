import subprocess
import os
import time
import glob
from threading import Timer

class DiscoverProcessTrees:
    '''
    Call the inductive miner available in Prom using the cli
    see readme file from github
    '''
    def __init__(self, settings):
        self.settings = settings
        self.cmd = "/Applications/ProM-6.7.app/Contents/Resources/ProM67cli.sh -f /Applications/ProM-6.7.app/Contents/Resources/xes-inductive-miner.sh"

    def mineTree(self, names):
        '''
        From time to time, some process trees were lost in the process
        Hence, we check at the end that we get as many process trees as input xes file
        If not, we run the process again
        '''
        folder = self.settings['folder_name'][:-1]
        def run():
            while len(glob.glob('current_file/*')) >= 1:
                time.sleep(5)
                print('Had to wait because another process is using PROM')
            open('current_file/'+folder, 'a').close()

            proc = subprocess.Popen(self.cmd.split(" "), stdout=open("/dev/null", "w"), cwd="/Applications/ProM-6.7.app/Contents/Resources/", stderr=open("/dev/null", "w"))

            timer = Timer(40, proc.kill)
            try:
                timer.start()
                proc.communicate()
            finally:
                timer.cancel()
                if os.path.exists('current_file/'+folder):
                    os.remove('current_file/'+folder)

        def check_if_all_files(names):
            for name in names:
                if not os.path.exists('xes_temp_output/'+folder+'/'+name):
                    return False
            return True

        i = 0
        while check_if_all_files(names) == False:
            i+=1
            print ('running Prom...(iteration',i,')')
            run()
        print('end Prom...')



import shutil
import os

class Utils:

    def create_empty_folder(self, path):
        if os.path.exists(path):
            shutil.rmtree(path)
        os.makedirs(path)



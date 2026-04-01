import joblib
import os
import time

class ModelManager:

    def __init__(self, model_path):
        self.model_path = model_path
        self.model = joblib.load(model_path)
        self.last_modified = os.path.getmtime(model_path)

    def get_model(self):
        return self.model

    def check_reload(self):
        current_modified = os.path.getmtime(self.model_path)

        if current_modified != self.last_modified:
            print("Reloading updated ML model...")
            self.model = joblib.load(self.model_path)
            self.last_modified = current_modified
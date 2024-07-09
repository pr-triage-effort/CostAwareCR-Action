import random
from typing import Optional


class Analyzer:
    def __init__(self, path=None) -> None:
        if path:
            self.init_model(path)
        else:
            self.model = None
            print("No model found! Analyzer initialized in STUB mode")

    def init_model(self, path: str) -> None:
        print("Not yet implemented")

    def analyze_prs(self, pr_features: list) -> list:
        results = []

        if self.model is not None:
            print("Not yet implemented")
        else:
            for pr in pr_features:
                results.append(random.randint(0, 100))

        return results

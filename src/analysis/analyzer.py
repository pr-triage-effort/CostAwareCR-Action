import random
import pickle
import copy
import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.exceptions import NotFittedError
from sklearn.utils.validation import check_is_fitted

from ml_model.model_configs import FEATURES, NUMERICAL_FEATURES, BOOL_FEATURES, weights as w, rules as r

class Analyzer:
    def __init__(self, path=None) -> None:
        if path:
            self.init_model(path)
        else:
            self.model = False
            print("No model found! Analyzer initialized in STUB mode")

    def init_model(self, path: str) -> None:
        self.preprocessing_metadata = pickle.load(open(path, 'rb'))
        self.weights = w
        self.rules = r
        self.model = True

    def analyze_prs(self, pr_features: list[dict]) -> list:
        results = []

        if self.model:
            for pr in pr_features:
                pr_result = {
                    'title': pr['title'],
                    'number': pr['number'],
                    'probability': predict_value(pr['features'], self.preprocessing_metadata, self.weights, self.rules)
                }
                results.append(pr_result)
        else:
            for pr in pr_features:
                pr_result = {
                    'title': pr['title'],
                    'number': pr['number'],
                    'probability': random.random()
                }
                results.append(pr_result)

        return results

def predict_value(row, preprocess_metadata, weights, rules, features_order = FEATURES,):
    
    row_np = np.array([row[f] for f in features_order])
    preprocessed_row_np, _ = preprocess(pd.DataFrame([row_np], columns=features_order), preprocess_metadata)
    preprocessed_row_dict = preprocessed_row_np.to_dict(orient='records')[0]
    row_rules = []
    for rule_name, rule_str in rules.items() : 
        row_rules.append(evaluate_rule(preprocessed_row_dict, rule_str))
    
    ready_row = np.array([1] + preprocessed_row_np.values.tolist()[0] + row_rules)
    prediction = np.matmul(weights.T, ready_row)
    final_prediction = 1.0/(1.0 + np.exp(-prediction))
    return final_prediction
    
     
def evaluate_rule(row, rule_str): 
    literals = rule_str.split(' & ')
    for literal in literals: 
        splitted_literal = literal.split(' ')
        feature_name, operator, value = splitted_literal[0], splitted_literal[1], splitted_literal[2]
        value = float(value)
        if operator == '<=': 
            res = row[feature_name] <= value
        if operator == '>' : 
            res = row[feature_name] > value
        if not(res) : 
            return 0
    return 1

def scale_data(data,features = NUMERICAL_FEATURES, scaler =  StandardScaler()) :
    result = copy.deepcopy(data)
    data_scaler = copy.deepcopy(scaler)
    try: 
        check_is_fitted(data_scaler) 
        result[features] = data_scaler.transform(result[features])
        
    except NotFittedError: 
        print('fit transform')
        result[features] = data_scaler.fit_transform(result[features]) 
    metadata = {
        'scaler' : data_scaler,
        'features' : features
    }
    return result, metadata

def preprocess(data,preprocessing_metadata) : 
    result = data.copy()
    all_metadata = {}
    #step 1: scaling 
    result, scaling_metadata = scale_data(result,preprocessing_metadata['scaling']['features'],
                                          scaler = preprocessing_metadata['scaling']['scaler'])
    all_metadata['scaling'] = scaling_metadata 
    return result, all_metadata
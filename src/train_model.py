import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os

def get_base_rate(hour: int, is_weekend: int) -> int:
    base_rate = 1

    if is_weekend:
        return 2
        
    if hour >= 8 and hour <= 10:
            base_rate = 15

    elif hour >= 11 and hour <= 14:
            base_rate = 25

    elif hour >= 15 and hour <= 17:
            base_rate = 12

    elif hour >= 18 and hour <= 20:
            base_rate = 8

    return base_rate

def generate_training_data(days:int = 30, seed:int = 42) -> pd.DataFrame:
    """
    Generates the training data and returns a pandas `DataFrame` object
    """
    rng = np.random.default_rng(seed)
    rows = []

    for day in range(days):
        day_of_week = day % 7
        is_weekend = False
        base_rate = 1
        label = "quiet"

        if day_of_week == 5 or day_of_week == 6:
            is_weekend = True

        for hour in range(24):

            base_rate = get_base_rate(hour = hour,is_weekend = is_weekend)

            event_count = rng.normal(loc=base_rate,scale=0.3*base_rate)
            event_count = max(0, int(event_count))
            
            if event_count > 10:
                label = "busy"
            else:
                label = "quiet"
            
            row = {"day_of_week" : day_of_week,
                   "hour" : hour,
                   "is_weekend" : is_weekend,
                   "event_count" : event_count,
                   "label" : label}
            rows.append(row)
    return pd.DataFrame(rows)

def train_and_save(output_dir = "models"):
    model_path = os.path.join(os.curdir,output_dir)
    if not os.path.exists(model_path):
         os.makedirs(model_path)
    
    df = generate_training_data()

    input_features = df[["day_of_week","hour","is_weekend"]]
    target_labels = df["label"]

    x_train, x_test, y_train, y_test = train_test_split(input_features.to_numpy(), target_labels.to_numpy(), test_size=0.2, random_state=42)
    rfc = RandomForestClassifier(n_estimators=50, random_state=42)
    rfc.fit(x_train,y_train)
    y_pred = rfc.predict(x_test)
    print("Model eval")
    print(classification_report(y_true=y_test,y_pred=y_pred))

    model_path = os.path.join(model_path,"busy_predictor.joblib")
    joblib.dump(rfc, model_path)

    print("file saved at : ", model_path)
    return rfc

if __name__ == "__main__":
     train_and_save()

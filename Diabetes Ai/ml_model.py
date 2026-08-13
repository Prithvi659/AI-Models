import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report

from pathlib import Path
path = Path(__file__).parent / "diabetes1.csv"
class Logistic():

    def call_csv(self):
        self.df = pd.read_csv(path)

    def clean_df(self):
        self.call_csv()              
        self.X = self.df.drop(columns=["Outcome"])
        self.y = self.df["Outcome"]

    def split_data(self):
        self.clean_df()              
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            self.X,
            self.y,
            test_size=0.2,
            random_state=42
        )

    def create_model(self):
        self.split_data()           
        self.lg_model = LogisticRegression(max_iter=1000)
        self.lg_model.fit(self.X_train, self.y_train)
        self.y_pred = self.lg_model.predict(self.X_test)

    def get_results(self):
        self.create_model()         
        report = classification_report(self.y_test, self.y_pred)
        return report





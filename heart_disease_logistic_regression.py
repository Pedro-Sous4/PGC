import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt

class LogisticRegression:
    def __init__(self, learning_rate=0.01, n_iterations=1000):
        self.learning_rate = learning_rate
        self.n_iterations = n_iterations
        self.weights = None
        self.bias = None
        
    def sigmoid(self, z):
        return 1 / (1 + np.exp(-z))
    
    def fit(self, X, y):
        n_samples, n_features = X.shape
        self.weights = np.zeros(n_features)
        self.bias = 0
        
        for _ in range(self.n_iterations):
            linear_model = np.dot(X, self.weights) + self.bias
            y_predicted = self.sigmoid(linear_model)
            
            dw = (1 / n_samples) * np.dot(X.T, (y_predicted - y))
            db = (1 / n_samples) * np.sum(y_predicted - y)
            
            self.weights -= self.learning_rate * dw
            self.bias -= self.learning_rate * db
    
    def predict(self, X):
        linear_model = np.dot(X, self.weights) + self.bias
        y_predicted = self.sigmoid(linear_model)
        y_predicted_cls = [1 if i > 0.5 else 0 for i in y_predicted]
        return np.array(y_predicted_cls)
    
    def predict_proba(self, X):
        linear_model = np.dot(X, self.weights) + self.bias
        y_predicted = self.sigmoid(linear_model)
        return y_predicted

def create_heart_disease_dataset(n_samples=1000):
    np.random.seed(42)
    
    age = np.random.normal(54, 9, n_samples)
    age = np.clip(age, 25, 80)
    
    sex = np.random.binomial(1, 0.5, n_samples)
    
    cp = np.random.choice([0, 1, 2, 3], n_samples, p=[0.3, 0.3, 0.25, 0.15])
    
    trestbps = np.random.normal(131, 17, n_samples)
    trestbps = np.clip(trestbps, 90, 200)
    
    chol = np.random.normal(246, 50, n_samples)
    chol = np.clip(chol, 120, 400)
    
    fbs = np.random.binomial(1, 0.15, n_samples)
    
    restecg = np.random.choice([0, 1, 2], n_samples, p=[0.5, 0.4, 0.1])
    
    thalach = np.random.normal(149, 23, n_samples)
    thalach = np.clip(thalach, 70, 220)
    
    exang = np.random.binomial(1, 0.35, n_samples)
    
    oldpeak = np.random.exponential(1.0, n_samples)
    oldpeak = np.clip(oldpeak, 0, 6)
    
    slope = np.random.choice([0, 1, 2], n_samples, p=[0.3, 0.5, 0.2])
    
    ca = np.random.choice([0, 1, 2, 3, 4], n_samples, p=[0.4, 0.3, 0.2, 0.08, 0.02])
    
    thal = np.random.choice([1, 2, 3], n_samples, p=[0.15, 0.55, 0.3])
    
    risk_score = (
        (age - 50) * 0.02 +
        sex * 0.3 +
        cp * 0.25 +
        (trestbps - 130) * 0.01 +
        (chol - 240) * 0.005 +
        fbs * 0.1 +
        restecg * 0.15 +
        (-thalch + 150) * 0.008 +
        exang * 0.35 +
        oldpeak * 0.3 +
        slope * 0.2 +
        ca * 0.4 +
        (thal == 2) * 0.1 +
        (thal == 3) * 0.6
    )
    
    probability = 1 / (1 + np.exp(-risk_score))
    target = np.random.binomial(1, probability)
    
    data = pd.DataFrame({
        'age': age,
        'sex': sex,
        'cp': cp,
        'trestbps': trestbps,
        'chol': chol,
        'fbs': fbs,
        'restecg': restecg,
        'thalach': thalach,
        'exang': exang,
        'oldpeak': oldpeak,
        'slope': slope,
        'ca': ca,
        'thal': thal,
        'target': target
    })
    
    return data

def evaluate_model(y_true, y_pred):
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    
    return accuracy, precision, recall, f1

def main():
    print("Creating synthetic heart disease dataset...")
    data = create_heart_disease_dataset(n_samples=1000)
    print(f"Dataset shape: {data.shape}")
    print(f"Target distribution:\n{data['target'].value_counts()}")
    
    X = data.drop('target', axis=1).values
    y = data['target'].values
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    print("\nTraining logistic regression model...")
    model = LogisticRegression(learning_rate=0.01, n_iterations=1000)
    model.fit(X_train_scaled, y_train)
    
    y_train_pred = model.predict(X_train_scaled)
    y_test_pred = model.predict(X_test_scaled)
    
    train_accuracy, train_precision, train_recall, train_f1 = evaluate_model(y_train, y_train_pred)
    test_accuracy, test_precision, test_recall, test_f1 = evaluate_model(y_test, y_test_pred)
    
    print("\nTraining Set Performance:")
    print(f"Accuracy: {train_accuracy:.4f}")
    print(f"Precision: {train_precision:.4f}")
    print(f"Recall: {train_recall:.4f}")
    print(f"F1-Score: {train_f1:.4f}")
    
    print("\nTest Set Performance:")
    print(f"Accuracy: {test_accuracy:.4f}")
    print(f"Precision: {test_precision:.4f}")
    print(f"Recall: {test_recall:.4f}")
    print(f"F1-Score: {test_f1:.4f}")
    
    print("\nConfusion Matrix (Test Set):")
    cm = confusion_matrix(y_test, y_test_pred)
    print(cm)
    
    sample_input = np.array([[70, 1, 4, 130, 322, 0, 2, 109, 0, 2.4, 2, 3, 3]])
    sample_input_scaled = scaler.transform(sample_input)
    
    prediction = model.predict(sample_input_scaled)[0]
    probability = model.predict_proba(sample_input_scaled)[0]
    
    print(f"\nSample Input: {sample_input[0]}")
    print(f"Prediction: {'Heart Disease' if prediction == 1 else 'No Heart Disease'}")
    print(f"Probability: {probability:.4f}")
    
    return model, scaler, data

if __name__ == "__main__":
    model, scaler, data = main()
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Flatten, Conv1D, MaxPooling1D, Dropout
from sklearn.model_selection import train_test_split
from bias import Bias
import numpy as np

def main():
    n = 1000
    duration = 2
    fs = 500
    online = True
    number_of_channels = 4
    port = '/dev/serial0'
    baudrate = 115200
    timeout = 1
    biasInstance = Bias(n=n, fs=fs, channels=number_of_channels, port=port, baudrate=baudrate, timeout=timeout)
    biasAI = AIBias()
    biasAI.collect_and_train(biasInstance)
    signals = biasInstance._biasReception.get_real_data(channels=number_of_channels, n=n)
    filtered_data = biasInstance._biasFilter.filter_signals(signals)
    # Process data
    times, eeg_signals = biasInstance._biasProcessing.process_signals(filtered_data)
    predicted_command = biasAI.predict_command(eeg_data=eeg_signals)
    print(f"Predicted Command: {predicted_command}")


class AIBias:
    def __init__(self):
        self.model = self.build_model()
        self.is_trained = False

    # Define getter
    def ai_is_trained(self):
        return self.is_trained
    
    def collect_and_train(self, bias_instance, commands):
        """
        Collects EEG data, extracts features, and trains the model.
        """
        X = []
        y = []
        label_map = {"forward": 0, "backward": 1, "left": 2, "right": 3, "stop": 4, "rest": 5}

        for command in commands:
            # Get real data from the Bias instance
            signals = bias_instance._biasReception.get_real_data(channels=bias_instance._number_of_channels, n=bias_instance._n)
            filtered_data = bias_instance._biasFilter.filter_signals(signals)
            _, eeg_signals = bias_instance._biasProcessing.process_signals(filtered_data)

            # Extract features and append to X
            features = self.extract_features(eeg_signals)
            X.append(features)
            y.append(label_map[command])

        # Convert X and y to numpy arrays
        X = np.array(X)
        y = np.array(y)

        # Train the model with the collected data
        self.train_model(X, y)

    def build_model(self):
        model = Sequential([
            Conv1D(filters=64, kernel_size=3, activation='relu', input_shape=(1000, 4)),  # Adjust input_shape based on your data
            MaxPooling1D(pool_size=2),
            Dropout(0.5),
            Flatten(),
            Dense(100, activation='relu'),
            Dense(50, activation='relu'),
            Dense(6, activation='softmax')  # 6 output classes (forward, backward, etc.)
        ])
        model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
        return model

    def extract_features(self, eeg_data):
        """
        Convert your eeg_data to a 2D array, shape it into the appropriate input format for your model.
        """
        features = []
        for ch, signals in eeg_data.items():
            for band_name, sig in signals.items():
                features.append(np.array(sig))
        features = np.array(features).T  # Transpose to get the correct shape
        return features

    def train_model(self, X, y):
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        self.model.fit(X_train, y_train, epochs=10, batch_size=32, validation_data=(X_test, y_test))
        self.is_trained = True

    def predict_command(self, eeg_data):
        if not self.is_trained:
            raise Exception("Model has not been trained yet.")
        features = self.extract_features(eeg_data)
        features = features.reshape(1, -1, self._number_of_channels)  # Reshape for the model input
        prediction = self.model.predict(features)
        return np.argmax(prediction, axis=1)[0]
    
if __name__ == "__main__":
    main()
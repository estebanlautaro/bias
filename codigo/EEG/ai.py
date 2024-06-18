import extraction
import pandas as pd
from keras.models import Sequential
from keras.layers import Dense, Dropout
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from keras.callbacks import EarlyStopping, ModelCheckpoint
import joblib
import reception

def prepare_data(eeg_data, n, duration, fs):
    df = extraction.extract_data(eeg_data, n, duration, fs)
    # Prepare the dataset
    X = df.drop(columns=['label'])
    y = pd.get_dummies(df['label'])  # One-hot encoding
    return X, y

def split_data(X, y):
    return train_test_split(X, y, test_size=0.3, random_state=42)

def standardize_data(X_train, X_test):
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test = scaler.transform(X_test)
    return X_train, X_test, scaler

def build_model(input_dim, output_dim):
    model = Sequential()
    model.add(Dense(128, input_dim=input_dim, activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(64, activation='relu'))
    model.add(Dropout(0.5))
    model.add(Dense(output_dim, activation='softmax'))
    model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
    return model

def train_model(model, X_train, y_train, X_val, y_val):
    early_stopping = EarlyStopping(monitor='val_loss', patience=10)
    model_checkpoint = ModelCheckpoint('best_model.h5', save_best_only=True, monitor='val_loss')
    history = model.fit(X_train, y_train, validation_data=(X_val, y_val), epochs=100, batch_size=32, callbacks=[early_stopping, model_checkpoint])
    model.save('final_model.h5')
    return history

def evaluate_model(model, X_test, y_test):
    loss, accuracy = model.evaluate(X_test, y_test)
    print(f'Accuracy: {accuracy}')

def save_model_and_scaler(model, scaler):
    model.save('wheelchair_model.h5')
    joblib.dump(scaler, 'scaler.save')

def main(n=1000, duration=2, fs=500):
    real_eeg_signal = reception.get_real_data(n, fs)
    X, y = prepare_data(real_eeg_signal, n, duration, fs)
    X_train, X_test, y_train, y_test = split_data(X, y)
    X_train, X_test, scaler = standardize_data(X_train, X_test)
    model = build_model(X_train.shape[1], y_train.shape[1])
    model = train_model(model, X_train, y_train, X_test, y_test)
    evaluate_model(model, X_test, y_test)
    save_model_and_scaler(model, scaler)

if __name__ == "__main__":
    main()
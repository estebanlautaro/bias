import numpy as np
import matplotlib.pyplot as plt
import scipy.interpolate
import mne
import numpy as np
from scipy.signal import butter, filtfilt, firwin, lfilter, iirfilter
import matplotlib.pyplot as plt
import graphingPython
from bias_reception import BiasReception

def main():
    n = 1000
    fs = 500
    number_of_channels = 4
    duration = n / fs

    biasreception = BiasReception()
    signals = biasreception.get_real_data(channels=number_of_channels, n=n, fs=fs, filter=True)

    for ch, signal in signals.items():
        t = np.arange(len(signals[ch])) / fs
        graphingPython.graph_signal_voltage_time(t=t, signal=np.array(signal), title="Signal {}".format(ch))

    biasfilter = FilterBias(eeg_data=signals, fs=fs, notch=True, bandpass=True, fir=True, iir=True)

    # Apply digital filtering
    filtered_data = biasfilter.filter_signals()

    # Calculate the time vector
    t = np.linspace(0, duration, n, endpoint=False)

    # Graph original signal
    graphingPython.graph_signal_voltage_time(t=t, signal=signals, title="Original Signal")

    # Print shape of signals
    print(f"Time vector shape: {t.shape}")
    print(f"Filtered data shape: {filtered_data.shape}")

    # Graph filtered signal
    graphingPython.graph_signal_voltage_time(t=t, signal=filtered_data, title="Filtered Signal")

    biasprocessing = ProcessingBias(n=n, fs=fs, eeg_data=signals)
    signals = biasprocessing.process_signals()

    graphingPython.plot_now()

class BiasDSP:
    def __init__(self, n, fs):
        self._n = n
        self._n = fs

class ProcessingBias(BiasDSP):
    def __init__(self, n, fs, eeg_data=None):
        self._n = n
        self._fs = fs
        self._duration = self._n / self._fs
        self._eeg_data = eeg_data

    def process_signals(self):
        processed_signals = {}

        for ch, signal in self._eeg_data.items():
            t, processed_signal = self.process_signal(signal)
            processed_signals[ch] = processed_signal
            
        return processed_signals

    def preprocess_signal(self):
        # Time vector
        t = np.linspace(0, self._duration, self._n, endpoint=False)

        if isinstance(self._eeg_data, np.ndarray):
            # Injection of real data
            signal = self._eeg_data
        elif isinstance(self._eeg_data, mne.epochs.Epochs):
            signal = self._eeg_data.get_data(copy=True).mean(axis=0)  # Average over epochs
            t = np.linspace(0, self._duration, len(signal), endpoint=False)
        else:
            raise ValueError("Unsupported data format")

        signal_fft_reduced, frequencies_reduced, signal_fft_magnitude_reduced = self.do_fft(signal)

        # Graph the entry signal
        graphingPython.graph_signal_voltage_time(t=t, signal=signal, title="Input signal")
        graphingPython.graph_signal_voltage_frequency(frequencies=frequencies_reduced, magnitudes=signal_fft_magnitude_reduced, title='Frequency spectrum of original signal')

        bands = {
            "alpha": (8, 13),
            "beta": (13, 30),
            "gamma": (30, 100),
            "delta": (0.5, 4),
            "theta": (4, 8)
        }

        filtered_signals = {}
        
        # Reconstruct the negative part of signals
        for band_name, band_range in bands.items():
            # Reconstruct and then apply Fourier in order to get the five signals over time
            filtered_signals[band_name] = self.filter_and_reconstruct(signal_fft_reduced, frequencies_reduced, band_range)
            # Plot the filtered waves in the time domain
            graphingPython.graph_signal_voltage_time(t=t, signal=filtered_signals[band_name].real, title=f"{band_name.capitalize()} over time")

        # New sampling rate for interpolation
        new_fs = self._fs * 10
        new_t = np.linspace(0, self._duration, int(self._duration * new_fs), endpoint=True)

        # Interpolate each wave
        interpolated_signals = {band_name: self.interpolate_signal(t, sig.real, new_t) for band_name, sig in filtered_signals.items()}

        # Plot the interpolated signals
        for band_name, sig in interpolated_signals.items():
            graphingPython.graph_signal_voltage_time(t=new_t, signal=sig, title=f"{band_name.capitalize()} interpolated")

        # Plot signals
        graphingPython.plot_now()

        # Return time vector and the signals already processed
        return t, interpolated_signals

    def do_fft(self, signal):
        # Apply Fourier Transform for the original signal
        signal_fft = np.fft.fft(signal)
        frequencies = np.fft.fftfreq(self._n, d=1/self._fs)
        signal_fft_magnitude = np.abs(signal_fft) / self._n

        # Eliminate the range of negative frequencies for original signal
        signal_fft_reduced = signal_fft[:self._n//2]
        frequencies_reduced = frequencies[:self._n//2]
        signal_fft_magnitude_reduced = signal_fft_magnitude[:self._n//2]

        return signal_fft_reduced, frequencies_reduced, signal_fft_magnitude_reduced

    def filter_and_reconstruct(self, signal_fft, frequencies, band):
        # Filter each band with the corresponding wave
        filtered_fft = np.zeros_like(signal_fft)
        band_indices = np.where((frequencies >= band[0]) & (frequencies <= band[1]))
        filtered_fft[band_indices] = signal_fft[band_indices] 
        # Reconstruct signal in the negative side
        filtered_fft[-band_indices[0]] = signal_fft[-band_indices[0]]
        # Apply inverse Fourier transform in order to obtain a signal in the time domain
        filtered_signal = np.fft.ifft(filtered_fft)
        return filtered_signal.real

    def interpolate_signal(self, t, signal, new_t):
        # Clip new_t to the range of t to avoid out-of-bounds values
        new_t_clipped = np.clip(new_t, t.min(), t.max())

        # Interpolate the signal to new time points
        interpolated_signal = scipy.interpolate.interp1d(t, signal, kind='cubic')(new_t_clipped)
        return interpolated_signal

class FilterBias(BiasDSP):
    def __init__(self, eeg_data, fs, notch, bandpass, fir, iir):
        self._notch = notch
        self._bandpass = bandpass
        self._fir = fir
        self._iir = iir
        self._eeg_signals = eeg_data
        self._fs = fs

    def filter_signals(self):
        filtered_signals = {}
        for ch, signal in self._eeg_signals.items():
            filtered_signal = self.digital_filtering(eeg_data=signal)
            filtered_signals[ch] = filtered_signal
        return filtered_signals

    def digital_filtering(self, eeg_data):
        try:
            # Handle NaN and infinite values
            eeg_data = self.preprocess_data(data=eeg_data)

            # Print data shape
            print(f"Original data shape: {eeg_data.shape}")

            # Check the dimensions of the eeg_data
            if eeg_data.ndim == 1:
                eeg_data = eeg_data.reshape(1, -1)
            
            if self._notch:
                # Remove power line noise
                eeg_data = self.butter_notch_filter(eeg_data, notch_freq=50)
                print(f"Data shape after notch filter: {eeg_data.shape}")
            
            if self._bandpass:
                # Apply high-pass and low-pass filters (bandpass)
                eeg_data = self.butter_bandpass_filter(eeg_data, lowcut=0.5, highcut=50)
                print(f"Data shape after bandpass filter: {eeg_data.shape}")
            
            if self._fir:
                # Apply FIR filter
                eeg_data = self.fir_filter(eeg_data, cutoff=30, numtaps=101)
                print(f"Data shape after FIR filter: {eeg_data.shape}")
            
            if self._iir:
                # Apply IIR filter
                eeg_data = self.iir_filter(eeg_data, cutoff=30)
                print(f"Data shape after IIR filter: {eeg_data.shape}")
            
            if eeg_data is not None:
                # Ensure the filtered data has the same length as t
                if eeg_data.shape[0] == 1:
                    eeg_data = eeg_data.flatten()

                return eeg_data

        # Handle errors in the digital filtering
        except Exception as e:
            print(f"An error occurred during filtering: {e}")
            return None

    # Preprocessing function to handle inf and NaN values
    def preprocess_data(self, data):
        # Replace inf with NaN
        data = np.where(np.isinf(data), np.nan, data)
        # Remove NaN values
        data = np.nan_to_num(data)
        return data

    def butter_bandpass_filter(self, data, lowcut, highcut, order=5):
        # Bandpass filter which allows a specific range of frequencies to pass
        nyquist = 0.5 * self._fs
        low = lowcut / nyquist
        high = highcut / nyquist

        # Range of the bandpass filter
        b, a = butter(order, [low, high], btype='band')

        # Check the padding length
        padlen = 3 * max(len(b), len(a)) 
        if data.shape[1] <= padlen:
            raise ValueError(f"The length of the input vector must be greater than padlen, which is {padlen}. Data length is {data.shape[1]}.")
        
        # Apply the bandpass filter
        y = filtfilt(b, a, data, axis=1)
        return y

    def butter_notch_filter(self, data, notch_freq, quality_factor=30):
        # Filter used to remove a specific frequency
        nyquist = 0.5 * self._fs
        notch = notch_freq / nyquist

        # Calculate the specific small band which will be filtered
        b, a = butter(2, [notch - notch / quality_factor, notch + notch / quality_factor], btype='bandstop')

        # Calculate the padding length
        padlen = 3 * max(len(b), len(a))
        if data.shape[1] <= padlen:
            raise ValueError(f"The length of the input vector must be greater than padlen, which is {padlen}. Data length is {data.shape[1]}.")
        
        # Apply the notch filter
        y = filtfilt(b, a, data, axis=1)
        return y

    def fir_filter(self, data, fs, cutoff, numtaps):
        # Design FIR filter using firwin
        fir_coefficients = firwin(numtaps, cutoff, fs=fs, pass_zero=True)  # Low-pass FIR filter
        # Apply the FIR filter using lfilter
        filtered_data = np.zeros_like(data)
        for i in range(data.shape[0]):
            filtered_data[i, :] = lfilter(fir_coefficients, 1.0, data[i, :])
        
        return filtered_data

    def iir_filter(self, data, cutoff):
        # Design IIR filter using iirfilter
        b, a = iirfilter(4, cutoff, fs=fs, btype='low', ftype='butter')  # Low-pass IIR filter
        # Apply the IIR filter using filtfilt for zero-phase filtering
        filtered_data = np.zeros_like(data)
        for i in range(data.shape[0]):
            filtered_data[i, :] = filtfilt(b, a, data[i, :])
        
        return filtered_data


# Create function with random values
def random_signal(self):
    # Set fixed parameter of amplitude for random EEG (uV)
    middle_amplitude = 0 
    standard_deviation = 5 # uV
    return np.random.normal(middle_amplitude, standard_deviation, self._n)

def square_signal(self, t):
    # Set parameters of square wave
    amplitude = 3
    frequency = 10

    # Save and return square wave
    return amplitude * np.sign(np.sin(2 * np.pi * frequency * t))

def model_signal(self):
    # Create a model eeg signal
    basic_eeg_signal = np.array([
        0.5, 0.4, 0.3, 0.2, 0.1,
        -0.1, -0.2, -0.3, -0.4, -0.5,
        0.8, 0.7, 0.6, 0.5, 0.4,
        -0.4, -0.5, -0.6, -0.7, -0.8,
        0.3, 0.2, 0.1, 0, -0.1,
        -0.2, -0.3, -0.4, -0.5, -0.6,
        0.7, 0.6, 0.5, 0.4, 0.3,
        -0.3, -0.4, -0.5, -0.6, -0.7,
        0.2, 0.1, 0, -0.1, -0.2,
        -0.3, -0.4, -0.5, -0.6, -0.7,
    ])


    eeg_signal = []

    # Repeat it until you have reached the number of samples
    repetitions = self._n // len(basic_eeg_signal)

    # Add repetitions to the signal
    eeg_signal = np.tile(basic_eeg_signal, repetitions)

    return eeg_signal

# Create an eeg signal with pure waves
def pure_signal_eeg(self, alpha_amp=1, alpha_freq=10, beta_amp=2, beta_freq=20,
                    gamma_amp=3, gamma_freq=40, delta_amp=4, delta_freq=2, theta_amp=5, theta_freq=5):

    # Time vector
    t = np.linspace(0, self._duration, int(self._duration * self._fs), endpoint=False)

    # Set each wave as a sine wave
    alpha_signal = alpha_amp * np.sin(2 * np.pi * alpha_freq * t)
    beta_signal = beta_amp * np.sin(2 * np.pi * beta_freq * t)
    gamma_signal = gamma_amp * np.sin(2 * np.pi * gamma_freq * t)
    delta_signal = delta_amp * np.sin(2 * np.pi * delta_freq * t)
    theta_signal = theta_amp * np.sin(2 * np.pi * theta_freq * t)
    signal = alpha_signal + beta_signal + gamma_signal + delta_signal + theta_signal

    return signal
    
if __name__ == "__main__":
    main()
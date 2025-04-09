import librosa
import numpy as np

def generate_lip_sync_data(audio_path):
    y, sr = librosa.load(audio_path)
    frame_length = int(sr * 0.05)
    hop_length = int(sr * 0.025)
    amplitude = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    amplitude = amplitude / np.max(amplitude)
    lip_sync_data = [{'time': i * 0.025, 'mouth_open': amp > 0.2} for i, amp in enumerate(amplitude)]
    return lip_sync_data

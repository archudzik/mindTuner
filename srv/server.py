import asyncio
import ctypes
import json
import os
import time
import websockets
import numpy as np
from ctypes import byref

# Load the DLL
dll_name = "mindtuner.dll"
dll_path = os.path.dirname(
    os.path.abspath(__file__)) + os.path.sep + dll_name
mindtuner = ctypes.WinDLL(dll_path)

# Define BSTR as a POINTER to WCHAR (wide character string)
BSTR = ctypes.POINTER(ctypes.c_wchar)

# Define the callback function type with __stdcall calling convention
CALLBACK = ctypes.WINFUNCTYPE(None, ctypes.c_long, ctypes.c_long)

# Define constants
MD_OK = 0
MD_FAILED = -1

# Define function prototypes
mindtuner.MD_Open.argtypes = [ctypes.c_short]
mindtuner.MD_Open.restype = ctypes.c_long

mindtuner.MD_IsDeviceConnected.argtypes = [ctypes.c_long]
mindtuner.MD_IsDeviceConnected.restype = ctypes.c_short

mindtuner.MD_Close.argtypes = [ctypes.c_long]
mindtuner.MD_Close.restype = None

mindtuner.MD_Get_Devices.argtypes = []
mindtuner.MD_Get_Devices.restype = ctypes.c_short

mindtuner.MD_Set_Sample_Rate.argtypes = [
    ctypes.c_long, ctypes.POINTER(ctypes.c_double)]
mindtuner.MD_Set_Sample_Rate.restype = ctypes.c_short

mindtuner.MD_Set_Calibration_Rate.argtypes = [
    ctypes.c_long, ctypes.POINTER(ctypes.c_double)]
mindtuner.MD_Set_Calibration_Rate.restype = ctypes.c_short

mindtuner.MD_Set_Calibration_Channel.argtypes = [ctypes.c_long, ctypes.c_short]
mindtuner.MD_Set_Calibration_Channel.restype = ctypes.c_short

mindtuner.MD_Start.argtypes = [ctypes.c_long]
mindtuner.MD_Start.restype = ctypes.c_short

mindtuner.MD_Stop.argtypes = [ctypes.c_long]
mindtuner.MD_Stop.restype = ctypes.c_short

mindtuner.MD_Set_Data_Callback.argtypes = [
    ctypes.c_long, CALLBACK, ctypes.c_long, ctypes.c_long]
mindtuner.MD_Set_Data_Callback.restype = None

mindtuner.MD_Get_Last_Error.argtypes = [ctypes.c_long]
mindtuner.MD_Get_Last_Error.restype = ctypes.c_long

mindtuner.MD_Get_Error_Message.argtypes = [ctypes.c_long]
mindtuner.MD_Get_Error_Message.restype = BSTR

mindtuner.MD_Get_Sample_Rate.argtypes = [ctypes.c_long]
mindtuner.MD_Get_Sample_Rate.restype = ctypes.c_double

mindtuner.MD_Get_Calibration_Rate.argtypes = [ctypes.c_long]
mindtuner.MD_Get_Calibration_Rate.restype = ctypes.c_double

mindtuner.MD_Total_Channels.argtypes = [ctypes.c_long]
mindtuner.MD_Total_Channels.restype = ctypes.c_short

mindtuner.MD_Get_Channel_Name.argtypes = [ctypes.c_long, ctypes.c_short]
mindtuner.MD_Get_Channel_Name.restype = BSTR

mindtuner.MD_Max_Value.argtypes = [ctypes.c_long, ctypes.c_short]
mindtuner.MD_Max_Value.restype = ctypes.c_double

mindtuner.MD_Min_Value.argtypes = [ctypes.c_long, ctypes.c_short]
mindtuner.MD_Min_Value.restype = ctypes.c_double

mindtuner.MD_Read_Last_Value.argtypes = [ctypes.c_long, ctypes.c_short]
mindtuner.MD_Read_Last_Value.restype = ctypes.c_double

# WebSocket connections
connected_clients = set()

# Define a global variable to hold the WebSocket server instance
websocket_server = None
event_loop = None

# Sampling
sample_rate_eeg = 250.0
sample_rate_gsr = 100.0
sample_rate_temp = 100.0

# Global variables for accumulating EEG data
e0_buffer = []
e0_bands = []
buffer_size = 256

# EEG bands
bands = {
    'delta': (0.5, 4),
    'theta': (4, 8),
    'alpha': (8, 13),
    'beta': (13, 30),
    'gamma': (30, 100)
}

# Utility functions


def bstr_to_string(bstr):
    if bstr:
        # Read the string as a regular C-style null-terminated string
        return ctypes.string_at(bstr)
    return ""


def set_calibration(device_handle, channel, desired_calibration_rate):
    print(f"Setting Calibration Channel to {channel}")
    if mindtuner.MD_Set_Calibration_Channel(device_handle, channel) != MD_OK:
        error = mindtuner.MD_Get_Last_Error(device_handle)
        error_msg = bstr_to_string(mindtuner.MD_Get_Error_Message(error))
        print(f"Failed to set the calibration channel. Error: {error_msg}")
        return False

    current_sample_rate = mindtuner.MD_Get_Sample_Rate(device_handle)
    calibration_rate = current_sample_rate / 2.0
    print(f"Attempting to set Calibration Rate to {calibration_rate} Hz")
    if mindtuner.MD_Set_Calibration_Rate(device_handle, byref(ctypes.c_double(calibration_rate))) != MD_OK:
        error = mindtuner.MD_Get_Last_Error(device_handle)
        error_msg = bstr_to_string(mindtuner.MD_Get_Error_Message(error))
        print(f"Failed to set the calibration rate. Error: {error_msg}")
        return False

    print(f"Requested Calibration Rate: {desired_calibration_rate} Hz")
    print(f"Actual Calibration Rate: {calibration_rate} Hz")
    return True


def configure_device(device_handle, sample_rate):
    print(f"Setting Sample Rate to {sample_rate}")
    actual_sample_rate = ctypes.c_double(sample_rate)
    if mindtuner.MD_Set_Sample_Rate(device_handle, byref(actual_sample_rate)) != MD_OK:
        error = mindtuner.MD_Get_Last_Error(device_handle)
        error_msg = bstr_to_string(mindtuner.MD_Get_Error_Message(error))
        print(f"Failed to set the sample rate. Error: {error_msg}")
        return False

    print(f"Requested Sample Rate: {sample_rate} Hz")
    print(f"Actual Sample Rate: {actual_sample_rate.value} Hz")

    total_channels = mindtuner.MD_Total_Channels(device_handle)
    print(f"Total Channels: {total_channels}")

    for ch in range(total_channels):
        channel_name = bstr_to_string(
            mindtuner.MD_Get_Channel_Name(device_handle, ch))
        max_value = mindtuner.MD_Max_Value(device_handle, ch)
        min_value = mindtuner.MD_Min_Value(device_handle, ch)
        print(
            f"Channel {ch}: {channel_name}, Max Value: {max_value}, Min Value: {min_value}")

    print("Configuration successful")
    return True


def my_callback(handle, userdata):
    last_value = mindtuner.MD_Read_Last_Value
    eeg_data = {}
    if last_value:
        eeg_data = {
            'e0': last_value(handle, 0),
            'e1': last_value(handle, 1),
            'e2': last_value(handle, 2),
            'e3': last_value(handle, 3),
            'e4': last_value(handle, 4),
            'e5': last_value(handle, 5),
            'e6': last_value(handle, 6),
            'e7': last_value(handle, 7),
            'gsr': last_value(handle, 8),
            'tmp': last_value(handle, 9),
            'ts': time.time_ns()
        }
    asyncio.run_coroutine_threadsafe(broadcast_data(eeg_data), event_loop)
    
# FFT functions

def calculate_fft(eeg_data, sampling_rate):
    n = len(eeg_data)
    fft_values = np.fft.fft(eeg_data)
    fft_values = fft_values[:n//2]  # Keep only the positive frequencies
    freqs = np.fft.fftfreq(n, 1/sampling_rate)[:n//2]
    
    # Normalizing the FFT output
    positive_fft_values = np.abs(fft_values) / n

    return freqs, positive_fft_values

def band_power(freqs, fft_values, band):
    # Find the indices of the frequency band
    band_indices = np.where((freqs >= band[0]) & (freqs <= band[1]))[0]
    
    # Handle cases where the band is not present in the frequencies
    if len(band_indices) == 0:
        return 0

    # Calculate the power in the band
    band_power_value = np.sum(fft_values[band_indices]**2) / len(band_indices)
    
    return band_power_value

# WebSockets functions


async def websocket_handler(websocket, path):
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            # Here we could handle messages from clients if needed
            pass
    finally:
        connected_clients.remove(websocket)


async def start_websocket_server():
    global websocket_server
    websocket_server = await websockets.serve(websocket_handler, "localhost", 8765)
    await websocket_server.wait_closed()


def stop_websocket_server():
    if websocket_server:
        websocket_server.close()


async def broadcast_data(eeg_data):
    global e0_buffer, e0_bands

    # Update the buffer with the new sample for e0
    e0_buffer.append(eeg_data['e0'])

    # Maintain the buffer size to the specified window size
    if len(e0_buffer) > buffer_size:
        e0_buffer.pop(0)  # Remove the oldest sample to maintain buffer size

    # Perform FFT if buffer is full
    if len(e0_buffer) == buffer_size:
        freqs, fft_values = calculate_fft(e0_buffer, sample_rate_eeg)
        e0_bands = {
            band: band_power(freqs, fft_values, freq_range)
            for band, freq_range in bands.items()
        }
        eeg_data['e0_bands'] = e0_bands
    

    data_to_send = json.dumps(eeg_data)
    if connected_clients:
        await asyncio.gather(*[client.send(data_to_send) for client in connected_clients])


# Main function


async def main_async():
    global event_loop
    event_loop = asyncio.get_event_loop()

    # WebSocket server task
    websocket_task = asyncio.create_task(start_websocket_server())

    # Get number of connected devices
    num_devices = mindtuner.MD_Get_Devices()
    if num_devices < 0:
        print("Failed to get the number of connected devices")
        return

    print(f"Number of connected devices: {num_devices}")

    for i in range(num_devices):
        # Open the device
        device_handle = mindtuner.MD_Open(i)
        if device_handle < 0:
            print(f"Failed to open the MindTuner device {i}")
            continue

        # Check if the device is connected
        connection_status = mindtuner.MD_IsDeviceConnected(device_handle)
        if connection_status == 1:
            print(f"The MindTuner device {i} is connected and open")
        else:
            print(f"MindTuner device {i} status: {connection_status}")
            mindtuner.MD_Close(device_handle)
            continue

        # Configure the device
        if not configure_device(device_handle, sample_rate_eeg):
            mindtuner.MD_Close(device_handle)
            continue

        # Set calibration
        if not set_calibration(device_handle, 8, sample_rate_gsr):
            mindtuner.MD_Close(device_handle)
            continue

        if not set_calibration(device_handle, 9, sample_rate_temp):
            mindtuner.MD_Close(device_handle)
            continue

        # Set the callback function
        callback_function = CALLBACK(my_callback)
        mindtuner.MD_Set_Data_Callback(device_handle, callback_function, int(1000 / sample_rate_eeg), 1)

        # Start data acquisition
        print("Starting data acquisition")
        if mindtuner.MD_Start(device_handle) != MD_OK:
            error = mindtuner.MD_Get_Last_Error(device_handle)
            error_msg = bstr_to_string(mindtuner.MD_Get_Error_Message(error))
            print(f"Failed to start data acquisition. Error: {error_msg}")
            mindtuner.MD_Close(device_handle)
            continue

        print("Data acquisition started")

        try:
            # Keep the program running until interrupted
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            print("Stopping data acquisition")
            if mindtuner.MD_Stop(device_handle) != MD_OK:
                error = mindtuner.MD_Get_Last_Error(device_handle)
                error_msg = bstr_to_string(mindtuner.MD_Get_Error_Message(error))
                print(f"Failed to stop data acquisition. Error: {error_msg}")
            else:
                print("Data acquisition stopped")
            mindtuner.MD_Close(device_handle)

    # Cancel the WebSocket server task gracefully
    websocket_task.cancel()
    try:
        await websocket_task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    asyncio.run(main_async())
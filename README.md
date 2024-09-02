# MindTuner X2-10 EEG Interface

 App file creates a real-time data visualization dashboard using WebSockets to receive streaming data and displays it using charts. The file uses Tailwind CSS for styling and ApexCharts for rendering the charts. The dashboard consists of two charts: a line chart for streaming data and a bar chart for FFT band data.

## Features

- **Real-time Data Visualization**: Updates dynamically as new data is received via WebSocket.
- **Stream Chart**: Displays continuous data over time.
- **FFT Chart**: Visualizes frequency bands (delta, theta, alpha, beta, gamma) based on FFT analysis.
- **Responsive Design**: Tailwind CSS ensures the dashboard adapts to various screen sizes.

## How It Works

1. **WebSocket Connection**: Connects to a WebSocket server at `ws://localhost:8765` to receive data.
2. **Data Handling**: Processes incoming JSON data, converts timestamps, and updates charts.
3. **Chart Updates**: Stream chart updates every 33ms; FFT chart updates every 250ms.

## Dependencies

- **Tailwind CSS**: For styling (loaded via CDN).
- **ApexCharts**: For charts (loaded via CDN).
- **WebSocket Server**: Required to provide real-time data.

## Usage

1. Run srv/server.py server locally using 32-bit (!!) Python.
2. Open the HTML file in a web browser.
3. The dashboard will start displaying data automatically.
"use client"
import { useEffect, useState } from "react";
import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official';

let socket = null;

export default function Page() {

    const [data, setData] = useState([]);

    useEffect(() => {
        if (socket) {
            return;
        }
        socket = new WebSocket("ws://localhost:8765");

        socket.addEventListener("open", event => {
            console.log("Connection established")
        });

        socket.addEventListener("message", event => {
            try {
                const receivedData = JSON.parse(event.data);
                // Convert timestamp to milliseconds since the Unix epoch
                const timestamp = new Date(receivedData.ts / 1000).getTime();
                const value = receivedData.e0;
                const newDataPoint = [timestamp, value]; // Create the Highcharts-expected format

                setData((currentData) => {
                    const newData = [...currentData, newDataPoint];
                    // Sort by timestamp, which is the first element of each data point array.
                    // Also we need to keep only last X data points. Otherwise chart will get messy.
                    return newData.slice(-600);
                });
            } catch (error) {
                console.error('Error parsing message data:', error);
            }
        });

        // Clean up function
        return () => {
            if (socket.readyState === WebSocket.OPEN) {
                socket.close();
                console.log('Disconnected');
            }
        };

    }, []);

    // Chart configuration options
    const chartOptions = {
        chart: {
            type: 'spline', // Defines the chart type as a spline (smoothed line chart)
            animation: false, // Enable animation for SVG elements
            marginRight: 10, // Margin on the right side of the chart
        },
        time: {
            useUTC: false, // Use local time instead of UTC
        },
        title: {
            text: 'Live Data Stream', // Chart title
        },
        xAxis: {
            type: 'datetime', // Configure x-axis to display dates and times
            tickPixelInterval: 1, // Distance between each tick mark on the x-axis
        },
        yAxis: {
            title: {
                text: 'mV', // y-axis title
            },
            min: -110,
            max: 110
        },
        legend: {
            enabled: false, // Disable chart legend
        },
        series: [{
            name: 'Live Data', // Series name
            data: data, // Chart data sourced from the state
        }],
    };

    return (
        <main className="flex min-h-screen flex-col items-center justify-between p-24">
            <div
                style={{
                    width: '800px',
                    height: '450px',
                    borderRadius: '8px',
                    boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)',
                    backgroundColor: 'white',
                    padding: '10px'
                }}
            >
                <HighchartsReact highcharts={Highcharts} options={chartOptions} />
            </div>
        </main>
    );
}

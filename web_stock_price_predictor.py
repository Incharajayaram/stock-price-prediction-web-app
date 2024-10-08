import streamlit as st
import os
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model  # type: ignore
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler

# Load the model
model_path = os.path.join(os.path.dirname(__file__), 'Latest_stcok_price_model.keras')
if os.path.exists(model_path):
    try:
        model = load_model(model_path)
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
else:
    st.error(f"Model file not found at {model_path}")

def online_learning(model, new_data, scaler):
    scaled_new_data = scaler.transform(new_data)
    x_new = scaled_new_data[:-1].reshape(1, -1, 1)
    y_new = scaled_new_data[-1].reshape(1, 1)

    prediction = model.predict(x_new)

    model.fit(x_new, y_new, epochs=1, verbose=0)

    return scaler.inverse_transform(prediction)[0][0]

def update_data_and_model(stock, model, scaler, last_100_days):
    end = datetime.now()
    start = end - timedelta(days=1)
    new_data = yf.download(stock, start, end)
    if not new_data.empty:
        new_close = new_data['Adj Close'].values[-1]
        last_100_days = np.append(last_100_days[1:], new_close)

        predicted_price = online_learning(model, last_100_days.reshape(-1, 1), scaler)

        st.write(f"New data point: {new_close}")
        st.write(f"Predicted next price: {predicted_price}")

    return last_100_days

st.markdown("<h2 style='text-align: left; color: white;'>Enter the Stock ID</h2>", unsafe_allow_html=True)
stock = st.text_input("Stock ID:", "GOOG")

end = datetime.now()
start = datetime(end.year - 20, end.month, end.day)

try:
    google_data = yf.download(stock, start, end)
    if google_data.empty:
        raise ValueError("No data found for the specified stock.")
except Exception as e:
    st.error(f"Error fetching data: {str(e)}")

if not google_data.empty:
    st.subheader("Stock Data")
    st.write(google_data)

    splitting_len = int(len(google_data) * 0.7)
    x_test = pd.DataFrame(google_data.Close[splitting_len:])

    def plot_graph(figsize, values, full_data, extra_data=0, extra_dataset=None):
        fig = plt.figure(figsize=figsize)
        plt.plot(values, 'Orange')
        plt.plot(full_data.Close, 'b')
        if extra_data:
            plt.plot(extra_dataset)
        return fig

    # Moving Averages
    for days in [250, 200, 100]:
        st.subheader(f'Original Close Price and MA for {days} days')
        google_data[f'MA_for_{days}_days'] = google_data.Close.rolling(days).mean()
        st.pyplot(plot_graph((15, 6), google_data[f'MA_for_{days}_days'], google_data, 0))

    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(x_test[['Close']])

    x_data = []
    y_data = []

    for i in range(100, len(scaled_data)):
        x_data.append(scaled_data[i-100:i])
        y_data.append(scaled_data[i])

    x_data, y_data = np.array(x_data), np.array(y_data)

    if 'model' in locals():  # Check if the model is loaded successfully
        predictions = model.predict(x_data)

        inv_pre = scaler.inverse_transform(predictions)
        inv_y_test = scaler.inverse_transform(y_data)

        plotting_data = pd.DataFrame(
            {
                'original_test_data': inv_y_test.reshape(-1),
                'predictions': inv_pre.reshape(-1)
            },
            index=google_data.index[splitting_len + 100:]
        )
        st.subheader("Original values vs Predicted values")
        st.write(plotting_data)

        st.subheader('Original Close Price vs Predicted Close price')
        fig = plt.figure(figsize=(15, 6))
        plt.plot(pd.concat([google_data.Close[:splitting_len + 100], plotting_data], axis=0))
        plt.legend(["Data- not used", "Original Test data", "Predicted Test data"])
        st.pyplot(fig)

    st.subheader("Future Close Price values")

    def predict_future_stock(no_of_days, prev_100):
        future_predictions = []
        # Scale and reshape the input data
        prev_100_scaled = scaler.transform(prev_100['Adj Close'].values.reshape(-1, 1)).reshape(1, -1, 1)

        for _ in range(no_of_days):
            next_day = model.predict(prev_100_scaled)[0, 0]
            future_predictions.append(next_day)
            prev_100_scaled = np.append(prev_100_scaled[:, 1:, :], [[[next_day]]], axis=1)

        return scaler.inverse_transform(np.array(future_predictions).reshape(-1, 1)).flatten()

    no_of_days = int(st.text_input("Enter the number of days to be predicted from current date: ", "10"))
    if no_of_days > 0:
        future_results = predict_future_stock(no_of_days, prev_100=google_data[['Adj Close']].tail(100))

        future_results = np.array(future_results).reshape(-1, 1)
        fig = plt.figure(figsize=(15, 5))
        plt.plot(pd.DataFrame(future_results), marker='o')
        for i in range(len(future_results)):
            plt.text(i, future_results[i], int(future_results[i][0]))
        plt.xlabel('Future days')
        plt.ylabel('Close Price')
        plt.title("Future Close price of stock")
        st.pyplot(fig)

    if st.button("Perform Online Learning"):
        last_100_days = google_data['Adj Close'].tail(100).values
        last_100_days = update_data_and_model(stock, model, scaler, last_100_days)
        st.write("Model updated with the latest data point.")
else:
    st.error("No stock data available to display.")

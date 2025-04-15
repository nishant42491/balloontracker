from sklearn.linear_model import LinearRegression
import pandas as pd
import joblib
import os

LAT_MODEL_PATH = "lat_model_linear.pkl"
LON_MODEL_PATH = "lon_model_linear.pkl"

def train_and_save_models(df: pd.DataFrame):
    df = df.sort_values(["id", "time_hour_ago"])
    df["vertical_speed"] = df.groupby("id")["alt"].diff(-1)
    df = df.dropna()

    X, y_lat, y_lon = [], [], []

    for _, g in df.groupby("id"):
        g = g.reset_index(drop=True)
        for i in range(len(g) - 1):
            X.append([
                g.loc[i, "time_hour_ago"],
                g.loc[i, "lat"],
                g.loc[i, "lon"],
                g.loc[i, "alt"],
                g.loc[i, "vertical_speed"]
            ])
            y_lat.append(g.loc[i + 1, "lat"])
            y_lon.append(g.loc[i + 1, "lon"])

    lat_model = LinearRegression()
    lon_model = LinearRegression()

    lat_model.fit(X, y_lat)
    lon_model.fit(X, y_lon)

    joblib.dump(lat_model, LAT_MODEL_PATH)
    joblib.dump(lon_model, LON_MODEL_PATH)
    print("✅ Linear models trained and saved.")

def predict_trajectory(df: pd.DataFrame, balloon_id: int, horizon=24):
    if not os.path.exists(LAT_MODEL_PATH) or not os.path.exists(LON_MODEL_PATH):
        raise FileNotFoundError("Models not found. Train them first with train_and_save_models.")

    lat_model = joblib.load(LAT_MODEL_PATH)
    lon_model = joblib.load(LON_MODEL_PATH)

    traj = df[df["id"] == balloon_id].sort_values("time_hour_ago")
    traj["vertical_speed"] = traj["alt"].diff(-1)
    traj = traj.dropna()

    if traj.empty:
        return None

    last = traj.iloc[0]  # most recent (time_hour_ago = 0)
    preds = []

    for step in range(horizon):
        x = [
            last["time_hour_ago"] - step,
            last["lat"],
            last["lon"],
            last["alt"],
            last["vertical_speed"]
        ]
        pred_lat = lat_model.predict([x])[0]
        pred_lon = lon_model.predict([x])[0]
        preds.append((pred_lat, pred_lon))

        # prepare input for next step
        last = last.copy()
        last["lat"] = pred_lat
        last["lon"] = pred_lon

    return preds


if __name__ == "__main__":

    from gbt import df

    train_and_save_models(df)

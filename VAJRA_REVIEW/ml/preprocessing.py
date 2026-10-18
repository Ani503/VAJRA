"""
Feature Preprocessing Pipeline for VAJRA Turbofan RUL and Anomaly Detection.
- Drops near-constant sensors via data-driven variance threshold.
- Clusters operating conditions (altitude, Mach, TRA) using KMeans.
- Normalizes sensor telemetry per operating condition.
- Computes rolling features (mean, std, slope) over a window.
- Computes deviation from each engine's early-life baseline.
"""

import numpy as np
import pandas as pd

try:
    import pandas.core.dtypes.dtypes as pdt
    if not hasattr(pdt, "StringDtype"):
        pdt.StringDtype = pd.StringDtype
except Exception:
    pass

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

CONDITION_COLS = ["altitude_ft", "mach", "throttle_resolver_angle"]
DEFAULT_WINDOW = 15
BASELINE_CYCLES = 20

class FeaturePipeline:
    def __init__(self, variance_threshold: float = 0.001, window_size: int = DEFAULT_WINDOW, n_clusters: int = 6):
        self.variance_threshold = variance_threshold
        self.window_size = window_size
        self.n_clusters = n_clusters
        self.selected_sensors = []
        self.condition_clusterer = None
        self.cluster_scalers = {}
        self.global_scaler = StandardScaler()
        self.feature_names = []

    def fit(self, df: pd.DataFrame):
        # 1. Identify raw sensor columns
        metadata_cols = {"engine_id", "cycle", "rul_true", "rul_capped_125"} | set(CONDITION_COLS)
        sensor_cols = [c for c in df.columns if c not in metadata_cols]

        # 2. Drop near-constant sensors (data-driven variance check)
        variances = df[sensor_cols].var()
        self.selected_sensors = [s for s in sensor_cols if variances[s] > self.variance_threshold]

        # 3. Fit Condition Clusterer on operating conditions
        self.condition_clusterer = KMeans(n_clusters=self.n_clusters, random_state=42, n_init=10)
        clusters = self.condition_clusterer.fit_predict(df[CONDITION_COLS])

        # 4. Fit Scaler per condition cluster
        for c in range(self.n_clusters):
            mask = (clusters == c)
            scaler = StandardScaler()
            if mask.sum() > 0:
                scaler.fit(df.loc[mask, self.selected_sensors])
            else:
                scaler.fit(df[self.selected_sensors])
            self.cluster_scalers[c] = scaler

        # Fit global scaler as fallback
        self.global_scaler.fit(df[self.selected_sensors])

        # Feature names will be built on transform
        return self

    def transform(self, df: pd.DataFrame) -> (pd.DataFrame, list):
        df_out = df.copy()

        # 1. Condition clusters
        if self.condition_clusterer:
            clusters = self.condition_clusterer.predict(df_out[CONDITION_COLS])
        else:
            clusters = np.zeros(len(df_out), dtype=int)

        # 2. Condition-normalized sensor values
        norm_sensor_data = np.zeros((len(df_out), len(self.selected_sensors)))
        for c in range(self.n_clusters):
            mask = (clusters == c)
            if mask.sum() > 0:
                scaler = self.cluster_scalers.get(c, self.global_scaler)
                norm_sensor_data[mask] = scaler.transform(df_out.loc[mask, self.selected_sensors])

        norm_cols = [f"{s}_norm" for s in self.selected_sensors]
        for idx, col in enumerate(norm_cols):
            df_out[col] = norm_sensor_data[:, idx]

        # 3. Engine-level baseline deviations and rolling features
        engineered_dfs = []
        for engine_id, group in df_out.groupby("engine_id", sort=False):
            grp = group.sort_values("cycle").copy()

            # Early life baseline (mean over first BASELINE_CYCLES)
            baseline = grp.iloc[:BASELINE_CYCLES][self.selected_sensors].mean()
            for s in self.selected_sensors:
                grp[f"{s}_dev_baseline"] = grp[s] - baseline[s]

            # Rolling stats on normalized sensors
            for s, s_norm in zip(self.selected_sensors, norm_cols):
                # Rolling mean
                grp[f"{s}_roll_mean"] = grp[s_norm].rolling(window=self.window_size, min_periods=1).mean()
                # Rolling std
                grp[f"{s}_roll_std"] = grp[s_norm].rolling(window=self.window_size, min_periods=1).std().fillna(0.0)
                # Rolling slope (difference between current and start of window divided by window)
                grp[f"{s}_roll_slope"] = (grp[s_norm] - grp[s_norm].shift(self.window_size - 1)).fillna(0.0) / float(self.window_size)

            engineered_dfs.append(grp)

        full_df = pd.concat(engineered_dfs, ignore_index=True)

        feature_cols = []
        # Include original selected sensors, normalized, deviations, and rolling stats
        for s in self.selected_sensors:
            feature_cols.append(s)
            feature_cols.append(f"{s}_norm")
            feature_cols.append(f"{s}_dev_baseline")
            feature_cols.append(f"{s}_roll_mean")
            feature_cols.append(f"{s}_roll_std")
            feature_cols.append(f"{s}_roll_slope")

        self.feature_names = feature_cols
        return full_df, feature_cols

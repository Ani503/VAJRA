import json
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
from sklearn.model_selection import GroupKFold

from ml.preprocessing import FeaturePipeline
from ml.inference import load_models, score_engine, explain_engine, ml_inference
from ml.live_scoring import LiveScorer

ROOT_DIR = Path(__file__).resolve().parent.parent

def test_ml_models_loaded():
    loaded = load_models()
    assert loaded is True
    assert ml_inference.xgb_model is not None
    assert ml_inference.iso_forest is not None
    assert ml_inference.pipeline is not None

def test_engine_group_split_no_leakage():
    # Verify that splitting by engine guarantees zero overlap between folds
    df = pd.read_csv(ROOT_DIR / "data" / "train_sensor_run_to_failure.csv")
    engine_ids = df["engine_id"].values
    gkf = GroupKFold(n_splits=5)

    for fold, (train_idx, val_idx) in enumerate(gkf.split(df, groups=engine_ids)):
        train_engines = set(df.iloc[train_idx]["engine_id"])
        val_engines = set(df.iloc[val_idx]["engine_id"])
        overlap = train_engines.intersection(val_engines)
        assert len(overlap) == 0, f"Data leakage detected in fold {fold}: {overlap}"

def test_ml_scoring_and_bounds():
    df = pd.read_csv(ROOT_DIR / "data" / "test_sensor_truncated.csv")
    tst_engine = df[df["engine_id"] == "TST-001"]

    scores = score_engine(tst_engine)
    assert "predicted_rul_cycles" in scores
    assert 1 <= scores["predicted_rul_cycles"] <= 125
    assert 0.0 <= scores["anomaly_score"] <= 1.0
    assert 0.0 <= scores["health_score"] <= 100.0
    assert scores["status"] in ("Healthy", "Watch", "Critical")
    assert 0.01 <= scores["failure_risk_7d"] <= 0.99

def test_shap_explanation_top_features():
    df = pd.read_csv(ROOT_DIR / "data" / "test_sensor_truncated.csv")
    tst_engine = df[df["engine_id"] == "TST-002"]

    explanation = explain_engine(tst_engine)
    top_5 = explanation.get("top_5_sensors", [])
    assert len(top_5) == 5, f"Expected 5 top sensors, got {len(top_5)}"
    for item in top_5:
        assert "sensor" in item
        assert "contribution" in item
        assert "component" in item
        assert item["component"] in ("Fan", "Compressor", "Combustion Chamber", "Turbine", "Shaft", "General")

def test_live_scorer_healthy_and_fault():
    scorer = LiveScorer()

    # Nominal healthy reading
    nominal = {
        "temp_c": 481.0,
        "pressure_kpa": 98.4,
        "vibration_mm_s": 2.05,
        "fan_rpm": 8950.0,
        "oil_pressure_psi": 55.0,
        "egt_c": 622.0,
    }
    h_res = scorer.score_reading(nominal, snapshot_rul=150, snapshot_health=92.0)
    assert h_res["status"] == "Healthy"
    assert h_res["health_score"] >= 70.0
    assert h_res["anomaly_score"] < 0.40

    # Severe fault reading
    fault = {
        "temp_c": 575.0,
        "pressure_kpa": 128.0,
        "vibration_mm_s": 7.2,
        "fan_rpm": 8980.0,
        "oil_pressure_psi": 34.0,
        "egt_c": 750.0,
    }
    f_res = scorer.score_reading(fault, snapshot_rul=150, snapshot_health=92.0)
    assert f_res["status"] == "Critical"
    assert f_res["health_score"] < 40.0
    assert f_res["components"]["Shaft"]["colour"] == "Red"

def test_metrics_json_integrity():
    metrics_path = ROOT_DIR / "ml" / "metrics.json"
    assert metrics_path.exists(), "ml/metrics.json must exist"

    with open(metrics_path, "r") as f:
        data = json.load(f)

    assert "models" in data
    assert "XGBoost" in data["models"]
    assert "RandomForest_Baseline" in data["models"]

    xgb = data["models"]["XGBoost"]
    rf = data["models"]["RandomForest_Baseline"]

    assert "test_rmse" in xgb and xgb["test_rmse"] > 0
    assert "test_mae" in xgb and xgb["test_mae"] > 0
    assert "nasa_asymmetric_score" in xgb and xgb["nasa_asymmetric_score"] > 0

    assert "test_rmse" in rf and rf["test_rmse"] > 0
    assert "test_mae" in rf and rf["test_mae"] > 0
    assert "nasa_asymmetric_score" in rf and rf["nasa_asymmetric_score"] > 0

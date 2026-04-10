import os
import pickle
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, average_precision_score, precision_recall_fscore_support

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


class DenoisingAutoencoder(nn.Module):
    def __init__(self, input_dim, bottleneck_dim=8, hidden_layers=1, dropout=0.0):
        super().__init__()

        if hidden_layers == 1:
            self.encoder = nn.Sequential(
                nn.Linear(input_dim, bottleneck_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            )
            self.decoder = nn.Sequential(
                nn.Linear(bottleneck_dim, input_dim)
            )

        elif hidden_layers == 2:
            hidden_dim = max(input_dim // 2, bottleneck_dim + 2)
            self.encoder = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, bottleneck_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            )
            self.decoder = nn.Sequential(
                nn.Linear(bottleneck_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, input_dim)
            )
        else:
            raise ValueError("hidden_layers must be 1 or 2")

    def forward(self, x):
        z = self.encoder(x)
        x_hat = self.decoder(z)
        return x_hat
    
#------------------------------------------------------------------------
# load trained model, scaler, threshold, feature names, and config
#------------------------------------------------------------------------

def load_anomaly_artifacts(artifact_dir: str, device: str = "cpu") -> dict:
    with open(os.path.join(artifact_dir, "preprocessor.pkl"), "rb") as f:
        loaded_preprocessor = pickle.load(f)

    with open(os.path.join(artifact_dir, "metadata.pkl"), "rb") as f:
        metadata = pickle.load(f)

    config = metadata["model_config"]

    model = DenoisingAutoencoder(
        input_dim=config["input_dim"],
        bottleneck_dim=config["bottleneck_dim"],
        hidden_layers=config["hidden_layers"],
        dropout=config["dropout"]
    )

    state_dict = torch.load(
        os.path.join(artifact_dir, "autoencoder_model.pt"),
        map_location=device
    )
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()

    return {
        "model": model,
        "preprocessor": loaded_preprocessor,
        "threshold": metadata["threshold"],
        "feature_names": metadata["feature_names"],
        "model_config": metadata["model_config"],
        "metrics": metadata["metrics"]
    }
    
#------------------------------------------------------------------------
# return sample-level anomaly scores and feature-level squared errors
#------------------------------------------------------------------------
def get_reconstruction_errors(model, X_array, device: str = "cpu"):
    model.eval()

    # convert DataFrame -> NumPy
    if hasattr(X_array, "to_numpy"):
        X_array = X_array.to_numpy()

    X_array = X_array.astype("float32")
    X_tensor = torch.from_numpy(X_array).to(device)

    with torch.no_grad():
        X_hat = model(X_tensor)

    sq_error = (X_tensor - X_hat) ** 2
    row_errors = sq_error.mean(dim=1).cpu().numpy()      # anomaly score per row
    feature_errors = sq_error.cpu().numpy()              # feature-level errors
    recon = X_hat.cpu().numpy()

    return row_errors, feature_errors, recon


#------------------------------------------------------------------------
# return top-k highest reconstruction-error features
#------------------------------------------------------------------------
def explain_top_features(feature_error_row: np.ndarray, feature_names: list, top_k: int = 5) -> list:
    top_idx = np.argsort(feature_error_row)[::-1][:top_k]
    return [
        {
            "feature": feature_names[i],
            "feature_error": float(feature_error_row[i])
        }
        for i in top_idx
    ]


def score_new_applicants(
    new_df: pd.DataFrame,
    loaded_artifacts: dict,
    top_k: int = 5,
    device: str = "cpu"
) -> list:
    """
    Score new applicants and return anomaly outputs.
    new_df must contain the same features used during training.
    """
    output_feature_names = loaded_artifacts["feature_names"]
    preprocessor = loaded_artifacts["preprocessor"]
    model = loaded_artifacts["model"]
    threshold = loaded_artifacts["threshold"]

    # Get the ORIGINAL input feature names from the preprocessor
    input_features = preprocessor.feature_names_in_

    # Force raw feature order to match training input
    X_new = new_df[input_features].copy()
    
    # Scale with fitted scaler
    X_new_processed = preprocessor.transform(X_new).astype(np.float32)

    # Get anomaly scores
    sample_errors, feature_errors, _ = get_reconstruction_errors(model, X_new_processed, device=device)
    pred_flags = (sample_errors > threshold).astype(int)

    outputs = []
    for i in range(len(X_new)):
        outputs.append({
            "anomaly_score": float(sample_errors[i]),
            "is_anomalous": bool(pred_flags[i]),
            "distribution_flag": "out_of_distribution" if pred_flags[i] == 1 else "in_distribution",
            "top_anomalous_features": explain_top_features(feature_errors[i], output_feature_names, top_k=top_k)
        })

    return outputs

#------------------------------------------------------------------------
# example call
#------------------------------------------------------------------------
'''
device = "cuda" if torch.cuda.is_available() else "cpu"
loaded = load_anomaly_artifacts("../models/ae_agent", device=device)

# Example new applicants
new_applicant = pd.DataFrame([{
    "person_age": 35,
    "person_income": 85000,
    "person_home_ownership": "RENT",
    "person_emp_length": 6,
    "loan_intent": "EDUCATION",
    "loan_grade": "C",
    "loan_amnt": 12000,
    "loan_int_rate": 11.5,
    "loan_percent_income": 0.1
}])

results = score_new_applicants(
    new_df=new_applicant,
    loaded_artifacts=loaded,
    top_k=5,
    device=device
)
'''
import numpy as np
from sklearn.metrics import roc_auc_score
import pandas as pd


def safe_auc(y_true, y_score):
    try:
        mask = ~np.isnan(y_score)
        if len(np.unique(y_true[mask])) < 2: 
            return 0.5
        
        roc_auc = roc_auc_score(y_true[mask], y_score[mask])
        return max(roc_auc, 1 - roc_auc)
    except Exception:
        return 0.5

def fast_calculate_vif(X, threshold=5.0):
    X_vif = X.loc[:, X.nunique() > 1].copy()
    dropped = True
    vifs = []
    
    while dropped:
        dropped = False
        corr_matrix = X_vif.corr().values
        try:
            inv_corr = np.linalg.inv(corr_matrix)
            vifs = np.diag(inv_corr)
        except np.linalg.LinAlgError:
            inv_corr = np.linalg.pinv(corr_matrix)
            vifs = np.diag(inv_corr)

        max_vif = np.max(vifs)
        if max_vif > threshold:
            max_idx = np.argmax(vifs)
            col_to_drop = X_vif.columns[max_idx]
            X_vif = X_vif.drop(columns=[col_to_drop])
            dropped = True
            
    vif_scores = {col: vif for col, vif in zip(X_vif.columns, vifs)}
    return X_vif, vif_scores

class AucVifSelector:
    def __init__(self, auc_threshold=0.52, stability_threshold=0.05, vif_threshold=5.0, top_k=25):
        self.auc_threshold = auc_threshold
        self.stability_threshold = stability_threshold
        self.vif_threshold = vif_threshold
        self.top_k = top_k
        self.selected_features_ = []
        self.vif_scores_ = {}
        self.train_auc_scores_ = {}
        self.val_auc_scores_ = {}
        self.audit_df_ = pd.DataFrame()
        
    def fit(self, X_train, y_train, X_val, y_val, iv_scores_dict=None):
        X_train_clean = X_train.replace([np.inf, -np.inf], np.nan).fillna(X_train.median(numeric_only=True))
        X_val_clean = X_val.replace([np.inf, -np.inf], np.nan).fillna(X_train.median(numeric_only=True))

        self.train_auc_scores_ = {col: safe_auc(y_train, X_train_clean[col]) for col in X_train_clean.columns}
        self.val_auc_scores_ = {col: safe_auc(y_val, X_val_clean[col]) for col in X_train_clean.columns}
        
        auc_selected_features = [
            col for col in X_train_clean.columns
            if (
                max(self.train_auc_scores_.get(col, 0.5), 1 - self.train_auc_scores_.get(col, 0.5)) >= self.auc_threshold and
                abs(self.train_auc_scores_.get(col, 0.5) - self.val_auc_scores_.get(col, 0.5)) < self.stability_threshold
            )
        ]
        print(f"   -> Features remaining after AUC Filtering: {len(auc_selected_features)}")
        
        X_train_auc = X_train_clean[auc_selected_features]
        
        if len(auc_selected_features) > 0:
            X_train_vif, self.vif_scores_ = fast_calculate_vif(X_train_auc, threshold=self.vif_threshold)
            surviving_features = list(X_train_vif.columns)
        else:
            surviving_features = []
            
        print(f"   -> Features remaining after VIF Filtering (<{self.vif_threshold}): {len(surviving_features)}")
            
        if surviving_features:
            auc_power = {col: max(self.train_auc_scores_.get(col, 0.5), 1 - self.train_auc_scores_.get(col, 0.5)) for col in surviving_features}
            sorted_features = sorted(surviving_features, key=lambda x: auc_power[x], reverse=True)
            self.selected_features_ = sorted_features[:self.top_k] if self.top_k else sorted_features
        else:
            self.selected_features_ = []
            
        print(f"   -> Features remaining after Top {self.top_k} Selection: {len(self.selected_features_)}")

        audit_data = []
        for col in self.selected_features_:
            auc = self.train_auc_scores_.get(col, 0.5)
            gini = 2 * max(auc, 1 - auc) - 1
            vif = self.vif_scores_.get(col, np.nan)
            iv = iv_scores_dict.get(col, np.nan) if iv_scores_dict else np.nan
            
            audit_data.append({
                'Feature': col,
                'Gini': round(gini, 4),
                'IV': round(iv, 4) if pd.notnull(iv) else iv,
                'VIF': round(vif, 4) if pd.notnull(vif) else vif
            })
        
        self.audit_df_ = pd.DataFrame(audit_data)
        return self
        
    def transform(self, X):
        missing = set(self.selected_features_) - set(X.columns)
        if missing:
            for col in missing:
                X[col] = 0.0
        return X[self.selected_features_]
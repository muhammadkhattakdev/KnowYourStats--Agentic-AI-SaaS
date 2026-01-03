import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import json


class DataAnalysisTools:
    """Collection of tools the agent can use for data analysis"""
    
    def __init__(self, dataframe: Optional[pd.DataFrame] = None):
        self.df = dataframe
    
    def get_basic_stats(self) -> Dict[str, Any]:
        """Get basic statistical summary"""
        if self.df is None:
            return {"error": "No dataset loaded"}
        
        stats = {
            "row_count": len(self.df),
            "column_count": len(self.df.columns),
            "columns": list(self.df.columns),
            "numeric_columns": list(self.df.select_dtypes(include=[np.number]).columns),
            "categorical_columns": list(self.df.select_dtypes(include=['object']).columns),
            "missing_values": self.df.isnull().sum().to_dict(),
            "summary_stats": self.df.describe().to_dict()
        }
        
        return stats
    
    def analyze_column(self, column_name: str) -> Dict[str, Any]:
        """Analyze a specific column"""
        if self.df is None or column_name not in self.df.columns:
            return {"error": f"Column {column_name} not found"}
        
        col = self.df[column_name]
        
        analysis = {
            "column": column_name,
            "dtype": str(col.dtype),
            "non_null_count": int(col.count()),
            "null_count": int(col.isnull().sum()),
            "unique_count": int(col.nunique())
        }
        
        if pd.api.types.is_numeric_dtype(col):
            analysis.update({
                "mean": float(col.mean()) if not col.empty else None,
                "median": float(col.median()) if not col.empty else None,
                "std": float(col.std()) if not col.empty else None,
                "min": float(col.min()) if not col.empty else None,
                "max": float(col.max()) if not col.empty else None,
                "quartiles": {
                    "q1": float(col.quantile(0.25)) if not col.empty else None,
                    "q2": float(col.quantile(0.50)) if not col.empty else None,
                    "q3": float(col.quantile(0.75)) if not col.empty else None,
                }
            })
        else:
            # Categorical analysis
            value_counts = col.value_counts()
            analysis.update({
                "top_values": value_counts.head(10).to_dict(),
                "mode": str(col.mode()[0]) if not col.mode().empty else None
            })
        
        return analysis
    
    def find_correlations(self, threshold: float = 0.5) -> Dict[str, Any]:
        """Find correlations between numeric columns"""
        if self.df is None:
            return {"error": "No dataset loaded"}
        
        numeric_df = self.df.select_dtypes(include=[np.number])
        
        if numeric_df.empty:
            return {"error": "No numeric columns found"}
        
        corr_matrix = numeric_df.corr()
        
        # Find strong correlations
        strong_correlations = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) >= threshold:
                    strong_correlations.append({
                        "column1": corr_matrix.columns[i],
                        "column2": corr_matrix.columns[j],
                        "correlation": float(corr_value),
                        "strength": "strong" if abs(corr_value) > 0.7 else "moderate"
                    })
        
        return {
            "correlation_matrix": corr_matrix.to_dict(),
            "strong_correlations": strong_correlations
        }
    
    def detect_outliers(self, column_name: str, method: str = "iqr") -> Dict[str, Any]:
        """Detect outliers in a numeric column"""
        if self.df is None or column_name not in self.df.columns:
            return {"error": f"Column {column_name} not found"}
        
        col = self.df[column_name]
        
        if not pd.api.types.is_numeric_dtype(col):
            return {"error": f"Column {column_name} is not numeric"}
        
        if method == "iqr":
            Q1 = col.quantile(0.25)
            Q3 = col.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = col[(col < lower_bound) | (col > upper_bound)]
            
            return {
                "method": "IQR",
                "column": column_name,
                "outlier_count": int(len(outliers)),
                "outlier_percentage": float(len(outliers) / len(col) * 100),
                "bounds": {
                    "lower": float(lower_bound),
                    "upper": float(upper_bound)
                },
                "outlier_values": outliers.tolist()[:20]  # Limit to 20
            }
        
        return {"error": "Unknown method"}
    
    def compare_groups(self, group_column: str, value_column: str) -> Dict[str, Any]:
        """Compare groups based on a categorical column"""
        if self.df is None:
            return {"error": "No dataset loaded"}
        
        if group_column not in self.df.columns or value_column not in self.df.columns:
            return {"error": "Columns not found"}
        
        grouped = self.df.groupby(group_column)[value_column].agg([
            'count', 'mean', 'median', 'std', 'min', 'max'
        ])
        
        return {
            "group_column": group_column,
            "value_column": value_column,
            "comparison": grouped.to_dict('index')
        }
    
    def get_time_series_insights(self, date_column: str, value_column: str) -> Dict[str, Any]:
        """Analyze time series data"""
        if self.df is None:
            return {"error": "No dataset loaded"}
        
        try:
            df_copy = self.df.copy()
            df_copy[date_column] = pd.to_datetime(df_copy[date_column])
            df_copy = df_copy.sort_values(date_column)
            
            # Basic trend
            values = df_copy[value_column].values
            trend = "increasing" if values[-1] > values[0] else "decreasing"
            
            # Calculate growth rate
            if len(values) > 1:
                growth_rate = ((values[-1] - values[0]) / values[0]) * 100
            else:
                growth_rate = 0
            
            return {
                "date_column": date_column,
                "value_column": value_column,
                "trend": trend,
                "growth_rate_percent": float(growth_rate),
                "start_value": float(values[0]) if len(values) > 0 else None,
                "end_value": float(values[-1]) if len(values) > 0 else None,
                "data_points": int(len(values))
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_top_n(self, column: str, n: int = 10, ascending: bool = False) -> Dict[str, Any]:
        """Get top N values from a column"""
        if self.df is None or column not in self.df.columns:
            return {"error": "Column not found"}
        
        sorted_values = self.df[column].sort_values(ascending=ascending).head(n)
        
        return {
            "column": column,
            "top_n": n,
            "order": "ascending" if ascending else "descending",
            "values": sorted_values.tolist()
        }
    
    def calculate_percentage_change(self, column: str) -> Dict[str, Any]:
        """Calculate percentage change in a column"""
        if self.df is None or column not in self.df.columns:
            return {"error": "Column not found"}
        
        col = self.df[column]
        
        if not pd.api.types.is_numeric_dtype(col):
            return {"error": "Column must be numeric"}
        
        pct_change = col.pct_change() * 100
        
        return {
            "column": column,
            "percentage_changes": pct_change.dropna().tolist()[:50],  # Limit output
            "avg_change": float(pct_change.mean()) if not pct_change.empty else None,
            "max_increase": float(pct_change.max()) if not pct_change.empty else None,
            "max_decrease": float(pct_change.min()) if not pct_change.empty else None
        }
    
    def get_distribution_summary(self, column: str, bins: int = 10) -> Dict[str, Any]:
        """Get distribution summary for a numeric column"""
        if self.df is None or column not in self.df.columns:
            return {"error": "Column not found"}
        
        col = self.df[column]
        
        if not pd.api.types.is_numeric_dtype(col):
            return {"error": "Column must be numeric"}
        
        hist, bin_edges = np.histogram(col.dropna(), bins=bins)
        
        return {
            "column": column,
            "bins": bins,
            "histogram": {
                "counts": hist.tolist(),
                "bin_edges": bin_edges.tolist()
            },
            "skewness": float(col.skew()) if len(col) > 0 else None,
            "kurtosis": float(col.kurtosis()) if len(col) > 0 else None
        }
"""Optional causal-analysis helpers; never prediction evidence."""
from __future__ import annotations
import numpy as np
class CausalInference:
    def difference_in_differences(self,treatment_group,control_group):
        import statsmodels.api as sm
        import pandas as pd
        t=pd.DataFrame(treatment_group).copy(); c=pd.DataFrame(control_group).copy()
        for d,g in ((t,1),(c,0)):
            if not {"outcome","post"}.issubset(d.columns): raise ValueError("groups need outcome and post")
            d["treatment"]=g
        data=pd.concat([t,c],ignore_index=True); data["interaction"]=data.treatment*data.post
        r=sm.OLS(data.outcome,sm.add_constant(data[["treatment","post","interaction"]])).fit()
        return {"causal_effect":float(r.params["interaction"]),"p_value":float(r.pvalues["interaction"]),"ci_lower":float(r.conf_int().loc["interaction",0]),"ci_upper":float(r.conf_int().loc["interaction",1])}
    def regression_discontinuity(self,running_variable,cutoff,outcome,bandwidth=0.05):
        import statsmodels.api as sm
        x=np.asarray(running_variable,float); y=np.asarray(outcome,float); mask=np.abs(x-cutoff)<bandwidth
        if mask.sum()<4: raise ValueError("insufficient observations near cutoff")
        z=np.column_stack([x[mask]-cutoff,(x[mask]>cutoff).astype(int)])
        r=sm.OLS(y[mask],sm.add_constant(z)).fit()
        return {"causal_effect":float(r.params[2]),"p_value":float(r.pvalues[2])}

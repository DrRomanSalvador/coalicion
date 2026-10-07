"""Global Sobol sensitivity analysis, loaded lazily."""
from __future__ import annotations
import numpy as np

def sobol_sensitivity_analysis(model, X_train, y_train, param_bounds, n_samples=512):
    if not param_bounds:
        raise ValueError("param_bounds cannot be empty")
    try:
        from SALib.sample import sobol as sobol_sample
        from SALib.analyze import sobol
    except ImportError as exc:
        raise RuntimeError("SALib is required for Sobol sensitivity analysis") from exc
    problem={"num_vars":len(param_bounds),"names":list(param_bounds),"bounds":list(param_bounds.values())}
    values=sobol_sample.sample(problem,n_samples,calc_second_order=True)
    y=[]
    for params in values:
        model.set_params(**dict(zip(problem["names"],params)))
        model.fit(X_train,y_train)
        pred=np.asarray(model.predict(X_train))
        y.append(float(np.mean(np.abs(pred-np.asarray(y_train)))))
    result=sobol.analyze(problem,np.asarray(y),print_to_console=False)
    return {"S1":result["S1"],"ST":result["ST"],"S2":result.get("S2")}

"""Optional LSTM adapter for sequential poll features."""
from __future__ import annotations
import numpy as np
class LSTM_ElectoralModel:
    def __init__(self, lookback=30, units=(64,32), dropout=0.2, random_seed=20261008):
        if lookback<1: raise ValueError("lookback must be positive")
        self.lookback=lookback; self.units=tuple(units); self.dropout=dropout; self.random_seed=random_seed; self.model=None
    def _build(self,n_features):
        import tensorflow as tf
        tf.keras.utils.set_random_seed(self.random_seed)
        m=tf.keras.Sequential([tf.keras.layers.Input(shape=(self.lookback,n_features))])
        for i,u in enumerate(self.units):
            m.add(tf.keras.layers.LSTM(u,return_sequences=i<len(self.units)-1)); m.add(tf.keras.layers.Dropout(self.dropout))
        m.add(tf.keras.layers.Dense(1)); m.compile(optimizer="adam",loss="mse",metrics=["mae"]); return m
    def create_sequences(self,data):
        a=np.asarray(data,dtype=float); a=a[:,None] if a.ndim==1 else a
        if len(a)<=self.lookback: raise ValueError("not enough observations")
        return np.stack([a[i-self.lookback:i] for i in range(self.lookback,len(a))]),a[self.lookback:]
    def fit(self,polls_history,epochs=20,batch_size=32,validation_split=0.0):
        X,y=self.create_sequences(polls_history); self.model=self._build(X.shape[-1])
        return self.model.fit(X,y,epochs=epochs,batch_size=batch_size,validation_split=validation_split,shuffle=False,verbose=0)
    def predict(self,recent_polls):
        if self.model is None: raise RuntimeError("fit must be called first")
        a=np.asarray(recent_polls,dtype=float); a=a[:,None] if a.ndim==1 else a
        if len(a)!=self.lookback: raise ValueError("wrong lookback")
        return self.model.predict(a[None,...],verbose=0)[0]

from src.longitudinal import correlation, moving_average, slope, volatility, zscore_outliers


def test_moving_average_and_slope():
    values=[1.0,2.0,3.0,4.0]
    assert moving_average(values,2)==[1.0,1.5,2.5,3.5]
    assert slope(values)==1.0


def test_volatility_and_outliers():
    values=[1,1,1,10]
    assert volatility(values) > 0
    assert zscore_outliers(values, threshold=1.5) == [3]


def test_correlation():
    assert correlation([1,2,3],[1,2,3]) == 1.0

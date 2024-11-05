import pandas as pd
import numpy as np



df = pd.DataFrame(np.array([[0,1], [2,3]]))

df.to_csv('test.csv')

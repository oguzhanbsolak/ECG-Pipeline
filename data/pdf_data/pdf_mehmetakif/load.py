import numpy as np
import pandas as pd

arr = np.load('/home/oguzhan/Desktop/ecg-pipeline/ECG-Pipeline/data/pdf_data/pdf_mehmetakif/extracted_ecgs/1/signals.npy', allow_pickle=True)
print(arr)
#convert to dataframe
df = pd.DataFrame(arr)
print(df)
#save to csv
df.to_csv('/home/oguzhan/Desktop/ecg-pipeline/ECG-Pipeline/data/pdf_data/pdf_mehmetakif/extracted_ecgs/1/signals.csv', index=False)
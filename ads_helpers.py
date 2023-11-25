import re

import pandas as pd
from sklearn import preprocessing


def txt_to_df(dataset_dict:dict, data_dir:str, dataset:str) -> pd.DataFrame:
    re_pattern = r'Timestamp:\s+(\d+\.\d+)\s+ID:\s+(\w+)\s+(\w+)\s+DLC:\s+(\d+)\s+((?:\w{2}\s+)+)'
    null_pattern = r'Timestamp:\s+(\d+\.\d+)\s+ID:\s+(\w+)\s+(\w+)\s+DLC:\s+(\d+)'

    timestamps = []
    ids = []
    dlcs = []
    data_fields = []
    with open(f'{data_dir}/{dataset_dict[dataset]}', 'r') as f:
        for line in f:
            re_match = re.match(re_pattern, line)
            if re_match:
                timestamp, msg_id, _, dlc, data_field = re_match.groups()
                timestamps.append(float(timestamp))
                ids.append(msg_id)
                dlcs.append(int(dlc))
                data_fields.append(data_field.strip())
            else:
                re_match = re.match(null_pattern, line)
                if re_match:
                    timestamp, msg_id, _, dlc = re_match.groups()
                    timestamps.append(float(timestamp))
                    ids.append(msg_id)
                    dlcs.append(int(dlc))
                    data_fields.append('')
    return pd.DataFrame({'Timestamp': timestamps, 'ID': ids, 'DLC': dlcs, 'Data': data_fields})


def encode_labels(df:pd.DataFrame, label_lst: list) -> pd.DataFrame:
    label_encoder = preprocessing.LabelEncoder()
    for label in label_lst:
        df[label] = label_encoder.fit_transform(df[label])
    return df
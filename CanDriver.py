import can
import time
import threading
import xgboost
import pickle
import sklearn
import logging
import pandas as pd
import matplotlib.pyplot as plt

import ads_helpers

# Create a logger for invalid message IDs
invalid_ids_logger = logging.getLogger('invalid_ids_logger')
invalid_ids_logger.setLevel(logging.INFO)
invalid_ids_handler = logging.FileHandler('invalid_message_ids.log')
invalid_ids_logger.addHandler(invalid_ids_handler)

# Create a logger for other information
message_logger = logging.getLogger('message_logger')
message_logger.setLevel(logging.INFO)
message_logger_handler = logging.FileHandler('message_log.log')
message_logger.addHandler(message_logger_handler)

# Create a logger for event information
event_logger = logging.getLogger('event_logger')
event_logger.setLevel(logging.INFO)
event_logger_handler = logging.FileHandler('event_log.log')
event_logger.addHandler(message_logger_handler)
# Load the model
with open('ads_model.pkl', 'rb') as file:
    ads_model = pickle.load(file)
## extract features from the datasets
## combine datasets
### 0 = no attack
### 1 = attack detected

data_dir = 'test_datasets'
dataset_filenames = {'attack_free': 'Attack_free_dataset.txt',
                     'dos_attack': 'DoS_attack_dataset.txt',
                     'fuzzy_attack': 'Fuzzy_attack_dataset.txt',
                     'impersonation_attack': 'Impersonation_attack_dataset.txt'}

data_dfs = {}
for dset in dataset_filenames:
    attack_label = 0 if dset == 'attack_free' else 1
    dset_df = ads_helpers.txt_to_df(dataset_filenames, data_dir, dset)
    dset_df['Attack'] = attack_label
    data_dfs[f'{dset}_df'] = dset_df
data_df = pd.concat(data_dfs.values(), keys=data_dfs.keys())
print("Dataset in memory")


## preprocess non-numerical features
# data_df = ads_helpers.encode_labels(data_df, label_lst=['ID', 'Data'])
# Function to convert DataFrame to CAN message
def dataframe_to_can(df):
    timestamp = float(df['Timestamp'])
    can_id = int(df['ID'], 16)
    dlc = int(df['DLC'])
    # Get the data string from the DataFrame
    data = bytes.fromhex(df['Data'].replace(' ', ''))

    message = can.Message(arbitration_id=can_id, data=data, timestamp=timestamp)
    return message


def msg_to_df(message):
    data = {
        'Timestamp': [],
        'ID': [],
        'DLC': [],
        'Data': []
    }

    data['Timestamp'].append(message.timestamp)
    data['ID'].append(hex(message.arbitration_id))
    data['DLC'].append(message.dlc)
    data['Data'].append(message.data.hex())  # Convert data bytes to hexadecimal string

    return pd.DataFrame(data)


bus1 = can.interface.Bus('CAN0', interface='virtual')
bus2 = can.interface.Bus('CAN0',
                         interface='virtual')
CAN_messages_total =[]
valid_ids = []  # Define valid IDs

for ID in data_dfs['attack_free_df']['ID']:
    valid_ids.append(ID)

# Function to filter messages by valid IDs
def filter_valid_messages(df):
    valid_messages = df[df['ID'].isin(valid_ids)]

    return pd.DataFrame(valid_messages)
# Gateway ECU with ML and Rule-based Filter



def gateway_ecu():
    internal_message_buffer = []
    bus_active = True
    # Process incoming messages
    while bus_active:
        message = bus2.recv(timeout=1)
        if message == None:
            bus_active = False
        else:
            df_message = msg_to_df(message)
            df_message['ID'] = df_message['ID'].apply(lambda x: x[2:].zfill(4))
            internal_message_buffer.append(df_message)
            message_logger.info(f"Gateway received: {message}")

    CAN_messages_total.append(internal_message_buffer)
    print("Gateway has received all pending messages\nInternal Message buffer size: " + str(len(internal_message_buffer)))
    message_buffer = pd.concat(internal_message_buffer,ignore_index=True)
    # Rule 1: Valid ID
    Validated_Messages = filter_valid_messages(message_buffer)
    # Convert message buffer IDs from strings to integers
    # Padding the valid_ids list with leading zeros
    #valid_ids_padded = [id_str.zfill(3) for id_str in valid_ids]
    print("Gateway removed " + str(len(message_buffer)- len(Validated_Messages) ) + " messages")
    message_logger.info("Gateway removed " + str(len(message_buffer)- len(Validated_Messages) ) + " messages")

    # # Further processing for valid messages
    # valid_df = df_buffered_data[df_buffered_data['ID'].isin(valid_ids)]
    # print(f"Valid Messages:\n {valid_df}")
    # # Isolate time domain violating messages
    # # Assuming 'Timestamp' is the name of the column containing timestamps
    # valid_df['Timestamp'] = pd.to_numeric(valid_df['Timestamp'])  # Convert column to numeric if needed


# Convert DataFrame into CAN messages
messages = []

data_df = data_df.sample(n=10000)

for index, row in data_df.iterrows():
    message = dataframe_to_can(row)
    messages.append(message)

for msg in messages:
    message_logger.info(f"Injecting into SIM: {msg}")
    bus1.send(msg)

gateway_ecu()
bus1.shutdown()
bus2.shutdown()
CAN_messages_total = CAN_messages_total[0]
CAN_messages_total = pd.concat(CAN_messages_total,ignore_index=True)
# Plotting

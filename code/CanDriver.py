import logging
import pickle
from collections import Counter

import can
import pandas as pd
from matplotlib import pyplot as plt

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

Message_Invalid_Count = 0
Message_Frequency_Count = 0
Message_Sequence_Count = 0
Message_TimeInterval_Count = 0
SAMPLE_SIZE = 10000
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
# for dataset in dataset_filenames:
dataset = 'dos_attack'
test_df = ads_helpers.txt_to_df(dataset_filenames, data_dir, dataset)
test_df = ads_helpers.encode_labels(test_df, label_lst=['ID', 'Data'])
pred = ads_model.predict(test_df)

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

    data['Timestamp'].append(float(message.timestamp))
    data['ID'].append(hex(message.arbitration_id))
    data['DLC'].append(message.dlc)
    data['Data'].append(message.data.hex())  # Convert data bytes to hexadecimal string

    return pd.DataFrame(data)


bus1 = can.interface.Bus('CAN0', interface='virtual')
bus2 = can.interface.Bus('CAN0',
                         interface='virtual')
CAN_messages_total = []
backup_non_can_buffer = []
CAN_secondary_buffer = []
valid_ids = []  # Define valid IDs
for ID in data_dfs['attack_free_df']['ID']:
    valid_ids.append(ID)


# Function to filter messages by valid IDs
def filter_valid_messages(df):
    valid_messages = df[df['ID'].isin(valid_ids)]

    return pd.DataFrame(valid_messages)

def filter_messages_from_base(base,filter):
    valid_messages = base[~base['ID'].isin(filter)]

    return pd.DataFrame(valid_messages)


# Gateway ECU with ML and Rule-based Filter

# Function to convert hexadecimal string to bytes
def hex_to_bytes(hex_str):
    # Split the hexadecimal string into pairs of bytes
    byte_list = [hex_str[i:i + 2] for i in range(0, len(hex_str), 2)]

    # Join the bytes with spaces to create a string
    bytes_string = ' '.join(byte_list)
    return bytes_string
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
    print(
        "Gateway has received all pending messages\nInternal Message buffer size: " + str(len(internal_message_buffer)))
    message_buffer = pd.concat(internal_message_buffer, ignore_index=True)
    # CAN_secondary_buffer = pd.concat(backup_non_can_buffer, ignore_index=True)
    # Rule 1: Valid ID
    Validated_Messages = filter_valid_messages(message_buffer)
    Validated_Messages_Backup = filter_valid_messages(blind_sample_set)
    # Convert message buffer IDs from strings to integers
    # Padding the valid_ids list with leading zeros
    # valid_ids_padded = [id_str.zfill(3) for id_str in valid_ids]
    Message_Invalid_Count = SAMPLE_SIZE - len(Validated_Messages)

    # Rule 2: Valid frequency

    random_frequency_messages = Validated_Messages['ID'].sample(n=3, random_state=42)
    # Filter the DataFrame for these 3 random IDs
    selected_messages = Validated_Messages[Validated_Messages['ID'].isin(
        random_frequency_messages)]  # Calculate time differences between consecutive timestamps for each message
    # Calculate average frequency for each message
    message_frequency = selected_messages.groupby('ID')['Timestamp'].agg(
        lambda x: 1 / (x.max() - x.min())).reset_index()
    message_frequency.columns = ['ID', 'Frequency']
    # Calculate average frequency in milliseconds

    # Check for messages with average frequency more than 20% above 10ms (12ms)
    invalid_messages = message_frequency[message_frequency['Frequency'] > 1 / (10 * 0.8)]
    Validated_Messages = filter_messages_from_base(Validated_Messages,invalid_messages)
    Message_Frequency_Count = Validated_Messages[Validated_Messages['ID'].isin(invalid_messages['ID'])].shape[0]

    # Rule 3: Sequence Rule
    sequence_ids = Validated_Messages.sample(3, random_state=42)
    sequence_messages = Validated_Messages[Validated_Messages['ID'].isin(sequence_ids)]

    invalid_ids = []
    for index, row in selected_messages.iterrows():
        if index + 1 < len(selected_messages) and selected_messages.iloc[index + 1]['ID'] not in sequence_ids:
            invalid_ids.append(row['ID'])
        elif index + 2 < len(selected_messages) and selected_messages.iloc[index + 2]['ID'] not in sequence_ids:
            invalid_ids.append(row['ID'])

    Validated_Messages = filter_messages_from_base(Validated_Messages,invalid_ids)
    Validated_Messages['Data'] = Validated_Messages['Data'].apply(hex_to_bytes)
    Message_Sequence_Count = len(invalid_ids)
    Encoded_Messages = ads_helpers.encode_labels(Validated_Messages_Backup, label_lst=['ID', 'Data'])
    predictions = ads_model.predict(Encoded_Messages)
    ECU_predictions = Counter(predictions)

    # Plotting
    categories = ['Valid Messages', 'Invalid Messages']
    counts = [ECU_predictions[0], ECU_predictions[1]]

    plt.figure(figsize=(8, 6))
    plt.bar(categories, counts, color=['blue', 'green', 'red'])
    plt.xlabel('Message Types')
    plt.ylabel('Counts')
    plt.title('Counts of CAN Messages')
    plt.savefig('CAN_messages_overall_result.png')

    # Plotting
    categories = ['Invalid ID', 'Invalid Frequency', 'Invalid Sequence']
    counts = [Message_Invalid_Count, Message_Frequency_Count, Message_Sequence_Count]

    plt.figure(figsize=(8, 6))
    plt.bar(categories, counts, color=['blue', 'green', 'red', 'orange'])
    plt.xlabel('Message Types')
    plt.ylabel('Counts')
    plt.title('Counts of CAN Messages')
    plt.savefig('InvalidMessageBreakdown.png')
    Rule_count = Message_Invalid_Count + Message_Frequency_Count + Message_Sequence_Count
    ML_count = ECU_predictions[1]
    # Plotting
    categories = ['Rule-Based', 'ML-Based']
    counts = [Rule_count, ML_count]

    plt.figure(figsize=(8, 6))
    plt.bar(categories, counts, color=['blue', 'green', 'red', 'orange'])
    plt.xlabel('Message Types')
    plt.ylabel('Counts')
    plt.title('Rule-based vs ML-Based Detection')
    plt.savefig('Rule_ML_Comparison.png')

    # Create a figure and axis
    fig, ax = plt.subplots()
    stats = {
        'Elements' : ['Rule-Based %', 'ML-Based %'],
        'Values' : [Rule_count/INVALID_MESSAGE_COUNT, ML_count/INVALID_MESSAGE_COUNT]
    }
    # Create a table
    table = ax.table(cellText=[stats['Values']], colLabels=stats['Elements'], loc='center')

    # Hide axis
    ax.axis('off')

    # Display the table
    plt.savefig('NetworkStats.png')

# Convert DataFrame into CAN messages
messages = []

sample_set = data_df.sample(n=SAMPLE_SIZE)

VALID_MESSAGE_COUNT = len(sample_set[sample_set['Attack'] == 0])
INVALID_MESSAGE_COUNT = len(sample_set[sample_set['Attack'] == 1])

blind_sample_set = sample_set.drop('Attack', axis=1)
for index, row in blind_sample_set.iterrows():
    message = dataframe_to_can(row)
    messages.append(message)

for msg in messages:
    message_logger.info(f"Injecting into SIM: {msg}")
    bus1.send(msg)

gateway_ecu()
bus1.shutdown()
bus2.shutdown()
CAN_messages_total = CAN_messages_total[0]
CAN_messages_total = pd.concat(CAN_messages_total, ignore_index=True)

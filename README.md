# Hybrid ADS in Automotive CAN Networks

Shared repository for Purdue-ECE547-Project (Hybrid Anomaly Detection System to Prevent Malicious Attacks on Automotive CAN Networks)

## Authors
- [Jonathan Cochran](https://github.com/ionzzu)
- [John Mushatt](https://github.com/JohnMushatt)
- Logan Coles

## Description

The objective of this project is to simulate a hybrid anomaly detection system (ADS) in a vehicle environment
- Hybrid ADS combines a machine learning filter and a rule-based filter
- Vehicle environment messages simulated with Python-can

## Results

Hybrid ADS blocked 85% of network attacks (See [project report](docs/ECE547_FinalProject.pdf))

## Base Environment Requirements

- Python 3.10.2 or higher

- pip 23.3.1 or higher

## Installation

1. Clone the repository

2. Install dependencies with `pip install -r requirements.txt`

## Fair Use Disclaimer

This project contains the CAN Dataset for intrusion detection (OTIDS) under test_datasets

### Fair Use Criteria

The use of OTIDS in this project is for academic purposes

### Acknowledgment

Hyunsung Lee, Seong Hoon Jeong and Huy Kang Kim, "OTIDS: A Novel Intrusion Detection System for In-vehicle Network by using Remote Frame", PST (Privacy, Security and Trust) 2017

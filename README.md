## What is AlbiPy?
AlbiPy is a network sniffing tool that allows direct access to the Albion Online Client's market data through Python. It captures market orders in real-time and can store them in CSV files or databases. AlbiPy can be paired with [AlbiVel](https://github.com/sanskar-mk2/AlbiVel), an enhanced marketplace explorer for Albion Online designed to work seamlessly with AlbiPy for market data collection.

**Note: AlbiPy has been tested on Linux and Windows. It is not guaranteed to work on older Windows versions or Mac OS. Contributions for testing on other operating systems are welcome.**

## What market data can AlbiPy access?
AlbiPy listens to the Albion Online client's UDP traffic to record and parse market orders. For each order, it captures:

- Order ID
- Unit price in silver 
- Total price in silver
- Quantity
- Item tier
- Order type (buy/sell)
- Buyer/seller names
- Item enchantment level
- Item quality level
- Location (e.g. Lymhurst, Bridgewatch, etc.)
- Expiry date
- Other metadata

## What are AlbiPy's limitations?
Since market data uses UDP, some packets may be malformed or unreadable. While AlbiPy attempts to fix common issues, some packets remain unparseable. These problematic packets are typically not the first ones received, so the most important orders are usually captured successfully. The raw logs and malformed packets are preserved for debugging or custom parsing.

The packet fixing methods may occasionally impact data accuracy. These fixes are optional and can be disabled if precise data is required for specific attributes.

## Example Scripts
AlbiPy includes several example scripts for common use cases:

- **record_to_csv_live.py**: Records market data to a CSV file, updating every 3 seconds
- **record_to_database_live.py**: Streams market data into a MySQL database in real-time

The CSV format includes headers for all data fields like Id, UnitPriceSilver, Amount, etc. The database script tracks best buy/sell prices for items across different locations.

## Getting Started
1. Download AlbiPy.py and the example scripts
2. For database usage, create a config.json with your MySQL credentials
3. Run scripts with administrative privileges (required for network sniffing)

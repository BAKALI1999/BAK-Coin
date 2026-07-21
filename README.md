# BAK-Coin 🚀

**BAK-Coin** is a secure, lightweight, and decentralized Peer-to-Peer (P2P) blockchain implementation built from scratch in Python. It features custom cryptographic engines, a command-line interface (CLI), node networking, and transaction management.

---

## 📂 Project Architecture

* **`blockchain.py`**: Core blockchain logic, block generation, proof-of-work, and chain validation.
* **`engine.py`**: Cryptographic hashing and core execution mechanics.
* **`node.py`**: P2P networking layer allowing nodes to communicate and sync.
* **`cli.py`**: Command-line interface for interacting with the blockchain and wallet.
* **`ecdsa.py`**: Custom digital signature algorithm implementation for secure transactions.
* **`demo_p2p.py`**: Simulation script for peer-to-peer network interactions.
* **`test_bak.py` & `test_smoke.py`**: Automated test suites for verifying system integrity.

---

## ⚙️ Getting Started

### Prerequisites
Make sure you have **Python 3.8+** installed on your system.

### Installation
Clone the repository to your local machine:

```bash
git clone [https://github.com/BAKALI1999/BAK-Coin.git](https://github.com/BAKALI1999/BAK-Coin.git)
cd BAK-Coin
🚀 Usage
Running Tests
To verify that everything is working properly, run the test suites:
python test_smoke.py
python test_bak.py
Running the CLI / Node
You can interact with the blockchain or start a node using the provided command-line tools:
python cli.py
🛡️ License
This project is open-source and available under the MIT License.

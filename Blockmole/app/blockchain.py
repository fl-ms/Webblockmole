from blockchain import blockexplorer

##############################

class BitcoinAddress:
    """
    This is a class for Bitcoinaddresses with all relevant data stored
    """
    def __init__(self, address, n_tx, total_received, total_sent, balance, last_tx_date, data_created_date, comment, transactions=None):
        
        self.address = address
        self.n_tx = n_tx
        self.total_received = total_received
        self.total_sent = total_sent
        self.balance = balance
        self.last_tx_date = last_tx_date
        self.data_created_date = 0
        self.comment = comment
        self.transactions = transactions
    
    def check_for_update(self, last_tx_time_old, address):
        api_address = blockexplorer.get_address(address)
        api_transactions = api_address.transactions
        last_tx_time = api_transactions[1].time
        if last_tx_time_old < last_tx_time:
            return True
        else:
            return False

##############################

def build(address, comment=""):
        # Builds the object with given attributes
        
        api_address = blockexplorer.get_address(address)
        api_transactions = api_address.transactions
        n_tx = api_address.n_tx
        total_received = api_address.total_received / 100000000
        total_sent = api_address.total_sent / 100000000
        balance = api_address.final_balance / 100000000
        if api_transactions:
            last_tx_date = api_transactions[0].time
        else:
            last_tx_date = 0
        #last_tx_date = datetime.utcfromtimestamp(api_transactions[-1].time).strftime('%Y-%m-%d %H:%M:%S')
        data_created_date = 0
        final_object = BitcoinAddress(address, n_tx, total_received, total_sent, balance, last_tx_date, data_created_date, comment, transactions=api_transactions)
        return final_object
